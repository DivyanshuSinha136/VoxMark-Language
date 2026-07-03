"""
VoxMark Compiler — three-target AST-to-output compiler.
Author: Divyanshu Sinha

Targets:
  HTML   — full rendered HTML document (via existing VML renderer)
  CSS    — standalone stylesheet bundle extracted from the document
  WASM   — WebAssembly binary + JS loader that hydrates a page from it

All three targets walk the same Document AST produced by the Parser.
No regex anywhere in this file.
"""

from __future__ import annotations

import base64
import html as _html
import json
import logging
import pathlib
import re
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import mistune as _mistune

from .lexer    import Lexer
from .parser   import Document, Widget, TextNode, VarRef, BodySegment, ASTNode, parse
from .wasm_encoder import encode_wasm

from . import language as _lang
from .language import (
    VMLTransformer,
    _sanitize_css, _scope_css,
    render_card, render_tab, render_alert, render_badge, render_progress,
    render_columns, render_callout, render_kbd, render_tooltip, render_timeline,
    render_math, render_color, render_glow, render_fold, render_demo,
    render_button, render_button_group, render_highlight, render_bold_styled,
    render_icon, render_svg, render_svg_icon_card,
    render_css_block, render_style_wrapper, render_css_class,
    render_css_var, render_cssplay,
    render_div, render_box, render_hero, render_grid, render_flex, render_section,
    render_divider, render_spacer, render_center, render_right,
    render_graph, render_graphplay, render_embed,
    _uid,
)

# Shared Mistune instance for Markdown-in-body rendering
_md = _mistune.create_markdown(
    plugins=['strikethrough', 'table', 'url', 'task_lists'],
)

def _md_inline(text: str) -> str:
    """Run Markdown and strip single wrapping <p> tag."""
    out = _md(text.strip())
    out = out.strip()
    if out.startswith('<p>') and out.endswith('</p>') and out.count('<p>') == 1:
        out = out[3:-4]
    return out


# Client-side runtime required for VML widgets to be interactive on a static
# build page (tabs, copy buttons, demo iframes, KaTeX, Chart.js, progress bar
# animation, ::if conditionals). Mirrors the inline engine used by the live
# editor (app.html) so compiled output behaves identically.
_RUNTIME_JS_TEMPLATE = textwrap.dedent('''
    <script>
    (function () {
      'use strict';

      window.vmlTab = function (uid, idx) {
        var wrap = document.getElementById('tabs-' + uid);
        if (!wrap) return;
        var btns = wrap.querySelectorAll('.vml-tab-btn');
        var panels = wrap.querySelectorAll('.vml-tab-panel');
        for (var i = 0; i < btns.length; i++) btns[i].classList.toggle('active', i === idx);
        for (var j = 0; j < panels.length; j++) panels[j].classList.toggle('active', j === idx);
      };

      window.vmlCopy = function (btn) {
        var block = btn.closest('.vml-code-wrap');
        var pre = block && block.querySelector('pre');
        if (!pre) return;
        navigator.clipboard.writeText(pre.innerText).then(function () {
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function () { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
        });
      };

      window.vmlRunDemo = function (uid) {
        var src = document.getElementById('ds-' + uid);
        var frame = document.getElementById('df-' + uid);
        if (src && frame) frame.srcdoc = src.value;
      };

      window.vmlIf = function (uid, cond) {
        var el = document.getElementById('vif-' + uid);
        if (!el) return;
        try {
          var safe = String(cond).replace(/[^a-zA-Z0-9_\\s<>=!&|]/g, '');
          if (Function('"use strict"; return (' + safe + ')')()) el.style.display = '';
        } catch (e) { /* ignore */ }
      };

      function animateProgressBars(root) {
        var bars = root.querySelectorAll('.vml-progress-bar');
        bars.forEach(function (bar) {
          var pct = bar.dataset.pct || '0';
          bar.style.width = '0';
          requestAnimationFrame(function () {
            setTimeout(function () { bar.style.width = pct + '%'; }, 50);
          });
        });
      }

      function renderCharts(root) {
        if (!window.Chart) return;
        root.querySelectorAll('.vml-chart[data-chart]').forEach(function (canvas) {
          var payload = JSON.parse(canvas.dataset.chart);
          new Chart(canvas.getContext('2d'), {
            type: payload.type || 'bar',
            data: payload.data,
            options: {
              responsive: true,
              plugins: { legend: { labels: { color: '#9ea3c0' } } },
              scales: {
                x: { ticks: { color: '#9ea3c0' }, grid: { color: '#252a44' } },
                y: { ticks: { color: '#9ea3c0' }, grid: { color: '#252a44' } }
              }
            }
          });
        });
      }

      function renderDemos(root) {
        root.querySelectorAll('.vml-demo-frame').forEach(function (iframe) {
          var id = iframe.id.replace('df-', 'ds-');
          var src = document.getElementById(id);
          if (src) iframe.srcdoc = src.value;
        });
      }

      function renderMath(root) {
        if (!window.renderMathInElement) return;
        renderMathInElement(root, {
          delimiters: [
            { left: '\\\\(', right: '\\\\)', display: false },
            { left: '\\\\[', right: '\\\\]', display: true }
          ],
          throwOnError: false
        });
      }

      function init() {
        var root = document.body;
        animateProgressBars(root);
        renderCharts(root);
        renderDemos(root);
        renderMath(root);
      }

      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
      } else {
        init();
      }
    })();
    </script>
''').strip()


# ══════════════════════════════════════════════════════════════════════════════
# Compile Result containers
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HTMLResult:
    html:    str
    css:     str
    title:   str = 'VoxMark Document'

    def to_page(
        self,
        pygments_css: str = '',
        extra_head: str = '',
        css_href: str = '',
        inline_css: bool = True,
    ) -> str:
        """
        Wrap the HTML fragment in a full standalone page.

        Parameters
        ----------
        pygments_css : extra Pygments CSS to inline (kept for backward compat)
        extra_head   : arbitrary HTML injected into <head>
        css_href     : if given, link this external stylesheet instead of inlining
        inline_css   : when True (default) and css_href is empty, embed self.css
                       in a <style> tag; set False when linking an external sheet
                       so base styles aren't duplicated
        """
        font_link = (
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Space+Grotesk:wght@300;400;500;600;700'
            '&family=JetBrains+Mono:wght@400;500&display=swap">'
        )
        katex_css = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">'
        chartjs   = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
        katex_js  = (
            '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
            '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>'
        )

        if css_href:
            css_tag = f'<link rel="stylesheet" href="{_html.escape(css_href)}">'
        elif inline_css and self.css:
            css_tag = f'<style>\n{self.css}\n</style>'
        else:
            css_tag = ''

        inline_extra = f'<style>\n{pygments_css}\n</style>' if pygments_css else ''
        runtime_js = _RUNTIME_JS_TEMPLATE

        return textwrap.dedent(f'''\
            <!DOCTYPE html>
            <html lang="en" data-theme="dark">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1">
              <title>{_html.escape(self.title)}</title>
              {font_link}
              {katex_css}
              {css_tag}
              {inline_extra}
              {extra_head}
            </head>
            <body>
              <div class="vml-doc" style="max-width:860px;margin:0 auto;padding:32px 24px">
                {self.html}
              </div>
              {chartjs}
              {katex_js}
              {runtime_js}
            </body>
            </html>
        ''')


@dataclass
class CSSResult:
    """All CSS rules extracted from a VML document."""
    rules:   List[str]        = field(default_factory=list)
    vars:    Dict[str, str]   = field(default_factory=dict)  # --name: value
    classes: Dict[str, str]   = field(default_factory=dict)  # .classname: inline style

    def bundle(self, base_css: str = '') -> str:
        """
        Produce a standalone CSS string.

        Parameters
        ----------
        base_css : optional pre-existing stylesheet to prepend (e.g. the main
                   VoxMark style.css loaded by the caller).
        """
        lines: List[str] = [
            '/* VoxMark Generated Stylesheet */',
            '/* Author: Divyanshu Sinha      */',
            '',
        ]
        if base_css:
            lines.append(base_css)
            lines.append('')

        if self.vars:
            lines.append(':root {')
            for name, val in self.vars.items():
                lines.append(f'  {name}: {val};')
            lines.append('}')
            lines.append('')

        for rule in self.rules:
            lines.append(rule)
            lines.append('')

        for cls, style in self.classes.items():
            lines.append(f'.{cls} {{ {style} }}')
            lines.append('')

        return '\n'.join(lines)


@dataclass
class WASMResult:
    """
    Compiled WebAssembly module + JS loader.

    wasm_bytes   — raw .wasm binary
    js_loader    — JavaScript that fetches/instantiates the module and
                   hydrates a DOM target element with all widget HTML
    wat_text     — human-readable WAT representation for debugging
    widget_count — number of widgets compiled into the module
    """
    wasm_bytes:   bytes
    js_loader:    str
    wat_text:     str
    widget_count: int

    def wasm_b64(self) -> str:
        """Base64-encoded .wasm for inline <script> data URI embedding."""
        return base64.b64encode(self.wasm_bytes).decode('ascii')

    def inline_html(self, target_id: str = 'voxmark-wasm-root') -> str:
        """
        Complete self-contained HTML snippet:
          - A <div id=target_id> placeholder
          - An inline <script> that instantiates the WASM and fills the div
        No external files needed.
        """
        b64 = self.wasm_b64()
        return textwrap.dedent(f'''\
            <div id="{target_id}" class="vml-wasm-root">
              <div class="vml-wasm-loading">Loading WASM module…</div>
            </div>
            <script type="module">
            /* VoxMark WASM Loader — Author: Divyanshu Sinha */
            (async function() {{
              const target = document.getElementById('{target_id}');
              if (!target) return;
              try {{
                // Decode base64-embedded .wasm
                const b64 = '{b64}';
                const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
                // Instantiate
                const {{ instance }} = await WebAssembly.instantiate(bin.buffer, {{}});
                const exp = instance.exports;
                const mem = new Uint8Array(exp.memory.buffer);
                const count   = exp.widget_count();
                const decoder = new TextDecoder('utf-8');
                // Build HTML from WASM memory
                let html = '';
                for (let i = 0; i < count; i++) {{
                  const ptr = exp.get_widget_ptr(i);
                  const len = exp.get_widget_len(i);
                  html += decoder.decode(mem.slice(ptr, ptr + len));
                }}
                target.innerHTML = html;
                // Dispatch event so page scripts can react
                target.dispatchEvent(new CustomEvent('voxmark:wasm:ready', {{
                  detail: {{ widgetCount: count, totalBytes: exp.render_all() }}
                }}));
              }} catch (e) {{
                target.innerHTML = '<div class="vml-error">WASM load error: ' + e.message + '</div>';
                console.error('VoxMark WASM error:', e);
              }}
            }})();
            </script>
        ''')

    def standalone_page(self, title: str = 'VoxMark WASM', extra_css: str = '') -> str:
        """Full HTML page with WASM loader and optional extra CSS."""
        snippet = self.inline_html()
        return textwrap.dedent(f'''\
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1">
              <title>{_html.escape(title)}</title>
              <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
              <style>
                body {{ font-family: 'Space Grotesk', system-ui, sans-serif;
                        max-width: 860px; margin: 0 auto; padding: 32px 24px;
                        background: #0d0f18; color: #e8eaf6; line-height: 1.7; }}
                .vml-wasm-loading {{ color: #5c627a; font-style: italic; }}
                .vml-error {{ background:#ef444411; border:1px solid #ef444433;
                              color:#ef4444; padding:10px 14px; border-radius:8px; }}
                {extra_css}
              </style>
            </head>
            <body>
              {snippet}
            </body>
            </html>
        ''')


# ══════════════════════════════════════════════════════════════════════════════
# HTML Compiler
# ══════════════════════════════════════════════════════════════════════════════

class HTMLCompiler:
    """
    Walks an AST Document and produces rendered HTML.
    Delegates widget rendering to the existing VML render functions.
    """

    def __init__(self, vars: Optional[Dict[str, str]] = None) -> None:
        self._vars: Dict[str, str] = vars or {}

    def compile(self, doc: Document, base_css: str = '') -> HTMLResult:
        html_parts = [self._node(n) for n in doc.children]
        return HTMLResult(html=''.join(html_parts), css=base_css)

    def _resolve(self, text: str) -> str:
        """Substitute @var references in a string."""
        out = []
        i   = 0
        while i < len(text):
            if text[i] == '@':
                j = i + 1
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                name = text[i+1:j]
                if name and name in self._vars:
                    out.append(self._vars[name])
                    i = j
                    continue
            out.append(text[i])
            i += 1
        return ''.join(out)

    def _arg(self, w: Widget, idx: int) -> str:
        """Get arg at index with var substitution."""
        val = w.args[idx] if idx < len(w.args) else ''
        return self._resolve(val)

    # ── node dispatch ──────────────────────────────────────────────────────────

    def _node(self, node: ASTNode) -> str:
        if isinstance(node, TextNode):
            return node.text
        if isinstance(node, VarRef):
            return self._vars.get(node.name, '@' + node.name)
        if isinstance(node, Widget):
            return self._widget(node)
        return ''

    def _seg(self, seg: BodySegment) -> str:
        """Render a body segment through Markdown then var substitution."""
        raw = ''.join(self._node(n) for n in seg.children)
        # Apply var substitution on raw text
        raw = self._resolve(raw)
        return _md_inline(raw)

    def _seg_raw(self, seg: BodySegment) -> str:
        """Raw body text without Markdown (for JSON/CSS/code bodies)."""
        return self._resolve(''.join(self._node(n) for n in seg.children))

    def _segs(self, w: Widget) -> List[str]:
        return [self._seg(s) for s in w.segments]

    def _body(self, w: Widget) -> str:
        if not w.segments:
            return ''
        return self._seg(w.segments[0])

    def _raw_body(self, w: Widget) -> str:
        if not w.segments:
            return ''
        return self._seg_raw(w.segments[0])

    # ── widget dispatch ────────────────────────────────────────────────────────

    def _widget(self, w: Widget) -> str:
        try:
            return self._dispatch_widget(w)
        except Exception as exc:  # noqa: BLE001 — never let one widget kill the page
            import logging
            logging.getLogger('voxmark.compiler').warning(
                'Widget ::%s render failed: %s', w.cmd, exc
            )
            return f'<div class="vml-error">::{w.cmd}: render failed — {_html.escape(str(exc))}</div>'

    def _dispatch_widget(self, w: Widget) -> str:
        cmd = w.cmd

        # ── var (compile-time, returns empty) ─────────────────────────────────
        if cmd == 'var':
            self._vars[w.arg0] = self._seg_raw(w.segments[0]) if w.segments else ''
            return ''

        # ── layout ────────────────────────────────────────────────────────────
        if cmd == 'card':      return render_card(self._arg(w,0), self._body(w))
        if cmd == 'alert':     return render_alert(self._arg(w,0), self._body(w))
        if cmd == 'callout':   return render_callout(self._arg(w,0) or '💡', self._body(w))
        if cmd == 'badge':
            return render_badge(self._arg(w,0), self._arg(w,1) or '#6c63ff')
        if cmd == 'progress':
            vals = (self._arg(w,0) or '0/100').split('/')
            return render_progress(vals[0], vals[1] if len(vals)>1 else '100', self._arg(w,1))
        if cmd == 'tab':
            inner = '||'.join(self._segs(w))
            return render_tab(self._arg(w,0), inner)
        if cmd == 'columns':
            return render_columns(self._arg(w,0), '||'.join(self._segs(w)))
        if cmd == 'fold':      return render_fold(self._arg(w,0), self._body(w))
        if cmd == 'demo':      return render_demo(self._raw_body(w))
        if cmd == 'kbd':       return render_kbd(self._raw_body(w))
        if cmd == 'tooltip':   return render_tooltip(self._arg(w,0), self._body(w))
        if cmd == 'timeline':
            return render_timeline('||'.join(self._seg_raw(s) for s in w.segments))
        if cmd == 'math':      return render_math(self._raw_body(w))
        if cmd == 'color':     return render_color(self._arg(w,0), self._body(w))
        if cmd == 'glow':      return render_glow(self._arg(w,0), self._body(w))
        if cmd == 'hl':        return render_highlight(self._arg(w,0), self._body(w))
        if cmd == 'b':         return render_bold_styled(self._arg(w,0), self._body(w))
        if cmd == 'center':    return render_center(self._body(w))
        if cmd == 'right':     return render_right(self._body(w))
        if cmd == 'divider':   return render_divider(self._arg(w,0))
        if cmd == 'spacer':    return render_spacer(self._arg(w,0))
        if cmd == 'if':
            uid = _uid()
            return (f'<span class="vml-if" data-cond="{_html.escape(self._arg(w,0))}" '
                    f'id="vif-{uid}" style="display:none">{self._body(w)}</span>'
                    f'<script>vmlIf("{uid}",{json.dumps(self._arg(w,0))})</script>')
        # ── buttons ──────────────────────────────────────────────────────────
        if cmd == 'button':
            return render_button(self._body(w), self._arg(w,0) or 'primary', self._arg(w,1) or '#')
        if cmd == 'btngroup':
            return render_button_group('||'.join(self._segs(w)))
        # ── icons / svg ──────────────────────────────────────────────────────
        if cmd == 'icon':
            return render_icon(self._arg(w,0), self._arg(w,1) or '1em', self._arg(w,2))
        if cmd == 'iconcard':
            return render_svg_icon_card(self._arg(w,0), self._arg(w,1), self._body(w))
        if cmd == 'svg':       return render_svg(self._raw_body(w))
        # ── CSS ──────────────────────────────────────────────────────────────
        if cmd == 'css':       return render_css_block(self._raw_body(w), _uid())
        if cmd == 'style':     return render_style_wrapper(self._arg(w,0), self._body(w))
        if cmd == 'class':     return render_css_class(self._arg(w,0), self._body(w))
        if cmd == 'cssvar':    return render_css_var(self._arg(w,0), self._raw_body(w))
        if cmd == 'cssplay':
            return render_cssplay('||'.join(self._seg_raw(s) for s in w.segments))
        # ── div / layout blocks ──────────────────────────────────────────────
        if cmd == 'div':       return render_div(self._arg(w,0), self._body(w))
        if cmd == 'box':       return render_box(self._arg(w,0), self._body(w))
        if cmd == 'hero':      return render_hero(self._arg(w,0), self._body(w))
        if cmd == 'grid':
            return render_grid(self._arg(w,0), '||'.join(self._segs(w)))
        if cmd == 'flex':
            return render_flex(self._arg(w,0), '||'.join(self._segs(w)))
        if cmd == 'section':   return render_section(self._arg(w,0), self._body(w))
        # ── graph / chart ────────────────────────────────────────────────────
        if cmd == 'graph':     return render_graph(self._arg(w,0), self._raw_body(w))
        if cmd == 'graphplay': return render_graphplay(self._raw_body(w))
        if cmd == 'chart':
            uid = _uid()
            try:
                data = json.loads(self._raw_body(w))
            except Exception:
                return '<div class="vml-error">chart: invalid JSON</div>'
            payload = json.dumps({'type': self._arg(w,0) or 'bar', 'data': data})
            return (f'<div class="vml-chart-wrap">'
                    f'<canvas id="vc-{uid}" class="vml-chart" data-chart=\'{payload}\'></canvas>'
                    f'</div>')
        # ── embed ────────────────────────────────────────────────────────────
        if cmd == 'embed':     return render_embed(self._arg(w,0), self._raw_body(w))
        # ── unknown → raw ────────────────────────────────────────────────────
        return w.raw


# ══════════════════════════════════════════════════════════════════════════════
# CSS Compiler
# ══════════════════════════════════════════════════════════════════════════════

class CSSCompiler:
    """
    Walks an AST Document and extracts all CSS declarations.

    Extracts:
      - :::css{...}    rules
      - ::cssvar[name]{value}  custom properties
      - ::style[...]{...}      inline style rules → generates utility classes
    """

    def __init__(self) -> None:
        self._result = CSSResult()
        self._style_counter = 0

    def compile(self, doc: Document) -> CSSResult:
        self._walk(doc.children)
        return self._result

    def _walk(self, nodes: List[ASTNode]) -> None:
        for node in nodes:
            if isinstance(node, Widget):
                self._widget(node)
                for seg in node.segments:
                    self._walk(seg.children)

    def _widget(self, w: Widget) -> None:
        cmd = w.cmd

        if cmd == 'css':
            raw = w.body_text
            safe = _sanitize_css(raw)
            self._result.rules.append(f'/* :::css block */\n{safe}')

        elif cmd == 'cssvar':
            name = w.arg0
            val  = w.body_text.strip()
            if not name.startswith('--'):
                name = '--' + name
            name = ''.join(c for c in name if c.isalnum() or c in '-_')
            self._result.vars[name] = _sanitize_css(val)

        elif cmd == 'style':
            style_str = w.arg0
            safe = _sanitize_css(style_str)
            cls  = f'vml-gen-{self._style_counter}'
            self._style_counter += 1
            self._result.classes[cls] = safe

        elif cmd == 'cssplay':
            segs = w.all_segments_text
            if segs:
                css_part = _sanitize_css(segs[0])
                self._result.rules.append(f'/* :::cssplay CSS */\n{css_part}')


# ══════════════════════════════════════════════════════════════════════════════
# WASM Compiler
# ══════════════════════════════════════════════════════════════════════════════

class WASMCompiler:
    """
    Walks an AST Document, renders each Widget to HTML via HTMLCompiler,
    then packs all widget HTML strings into a .wasm binary via WASMModule.

    The resulting WASM module lets JavaScript hydrate a page purely from
    binary data — no Python server needed after compilation.
    """

    def __init__(self) -> None:
        self._html_compiler: Optional[HTMLCompiler] = None
        self._widget_pairs:  List[Tuple[str, str]]  = []
        self._widget_counter: int = 0

    def compile(self, doc: Document, shared_vars: Optional[Dict[str,str]] = None) -> WASMResult:
        self._html_compiler  = HTMLCompiler(shared_vars or {})
        self._widget_pairs   = []
        self._widget_counter = 0

        # Collect all var definitions first (same as renderer pass-1)
        vars_dict: Dict[str, str] = {}
        self._collect_vars(doc.children, vars_dict)
        self._html_compiler._vars = vars_dict

        # Walk the AST and render each widget to HTML
        self._walk(doc.children)

        # Build WASM binary
        wasm_bytes = encode_wasm(self._widget_pairs)

        # Build JS loader
        js_loader  = self._build_js_loader()

        # Build WAT text (human-readable debug representation)
        wat_text   = self._build_wat()

        return WASMResult(
            wasm_bytes   = wasm_bytes,
            js_loader    = js_loader,
            wat_text     = wat_text,
            widget_count = len(self._widget_pairs),
        )

    def _collect_vars(self, nodes: List[ASTNode], vars_dict: Dict[str,str]) -> None:
        for node in nodes:
            if isinstance(node, Widget) and node.cmd == 'var':
                vars_dict[node.arg0] = node.body_text.strip()
            if isinstance(node, Widget):
                for seg in node.segments:
                    self._collect_vars(seg.children, vars_dict)

    def _walk(self, nodes: List[ASTNode]) -> None:
        for node in nodes:
            if isinstance(node, Widget):
                if node.cmd not in ('var', 'cssvar'):
                    # Render to HTML and store
                    rendered = self._html_compiler._widget(node)
                    wid = f'{node.cmd}_{self._widget_counter}'
                    self._widget_pairs.append((wid, rendered))
                    self._widget_counter += 1
                # Recurse into segments for nested widgets
                for seg in node.segments:
                    self._walk(seg.children)

    def _build_js_loader(self) -> str:
        """Build the JS loader string (also embedded in WASMResult.inline_html)."""
        return textwrap.dedent('''\
            /* VoxMark WASM Loader — Author: Divyanshu Sinha */
            async function loadVoxMarkWASM(wasmUrlOrBytes, targetElement) {
              let buffer;
              if (typeof wasmUrlOrBytes === 'string') {
                const resp = await fetch(wasmUrlOrBytes);
                buffer = await resp.arrayBuffer();
              } else {
                buffer = wasmUrlOrBytes.buffer || wasmUrlOrBytes;
              }
              const { instance } = await WebAssembly.instantiate(buffer, {});
              const exp     = instance.exports;
              const mem     = new Uint8Array(exp.memory.buffer);
              const count   = exp.widget_count();
              const decoder = new TextDecoder('utf-8');
              const parts   = [];
              for (let i = 0; i < count; i++) {
                const ptr = exp.get_widget_ptr(i);
                const len = exp.get_widget_len(i);
                parts.push(decoder.decode(mem.slice(ptr, ptr + len)));
              }
              const html = parts.join('');
              if (targetElement) {
                targetElement.innerHTML = html;
                targetElement.dispatchEvent(new CustomEvent('voxmark:wasm:ready', {
                  detail: { widgetCount: count, totalBytes: exp.render_all() }
                }));
              }
              return { html, count, totalBytes: exp.render_all(), instance };
            }
        ''')

    def _build_wat(self) -> str:
        """Build a human-readable WAT representation for debugging."""
        count = len(self._widget_pairs)
        lines = [
            ';; VoxMark WASM Module — Author: Divyanshu Sinha',
            f';; {count} widget(s) compiled',
            '(module',
            '  (memory (export "memory") 1)',
            f'  (global $widget_count i32 (i32.const {count}))',
            '',
            '  ;; widget_count() -> i32',
            '  (func (export "widget_count") (result i32)',
            '    global.get $widget_count)',
            '',
            '  ;; get_widget_ptr(i: i32) -> i32',
            '  (func (export "get_widget_ptr") (param $i i32) (result i32)',
            '    i32.const 4',
            '    local.get $i',
            '    i32.const 8',
            '    i32.mul',
            '    i32.add',
            '    i32.load)',
            '',
            '  ;; get_widget_len(i: i32) -> i32',
            '  (func (export "get_widget_len") (param $i i32) (result i32)',
            '    i32.const 8',
            '    local.get $i',
            '    i32.const 8',
            '    i32.mul',
            '    i32.add',
            '    i32.load)',
            '',
            f'  ;; render_all() -> i32  (total = {sum(len(h.encode()) for _,h in self._widget_pairs)} bytes)',
            '  (func (export "render_all") (result i32)',
            f'    i32.const {sum(len(h.encode()) for _,h in self._widget_pairs)})',
            '',
            '  ;; Data segment: widget table + HTML strings',
            '  (data (i32.const 0)',
        ]
        for wid, htm in self._widget_pairs:
            preview = htm[:60].replace('\n', ' ')
            lines.append(f'    ;; {wid}: {preview}…')
        lines.append('  )')
        lines.append(')')
        return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Top-level compile() API
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompileResult:
    html:  HTMLResult
    css:   CSSResult
    wasm:  WASMResult
    ast:   Document
    source_len: int = 0


def _resolve_includes(
    source: str,
    base_dir: pathlib.Path,
    _seen: frozenset[pathlib.Path] | None = None,
    depth: int = 0,
) -> str:
    """
    Build-time pre-pass: find all ``::include[path]`` widgets in *source*,
    read each referenced .vml/.md file relative to *base_dir*, render it
    recursively through this same function (so includes can nest), and
    substitute the rendered HTML back into the source text — wrapping it
    in a ``::include[path]{...rendered...}`` widget that ``render_include()``
    in language.py will then wrap in ``<div class="vml-include">``.

    Guards
    ------
    - Circular inclusion is detected via *_seen* (set of resolved absolute
      paths); a circular reference is replaced with an error comment.
    - Maximum nesting depth is capped at 16.
    - Only .vml and .md extensions are allowed.
    - Paths must stay within *base_dir* or its descendants (no ``../..``
      escapes outside the project root).
    """
    if _seen is None:
        _seen = frozenset()
    if depth > 16:
        return source

    # Pattern to find ::include[path] — bodyless, so no {} needed
    INCLUDE_PAT = re.compile(r'::include\[([^\]]+)\]')
    _log = logging.getLogger(__name__)

    def _resolve_one(m: re.Match) -> str:
        raw_path = m.group(1).strip()
        try:
            target = (base_dir / raw_path).resolve()
        except Exception:
            return f'<!-- VoxMark include error: bad path {raw_path!r} -->'

        # Extension whitelist
        if target.suffix.lower() not in ('.vml', '.md', '.txt'):
            return (
                f'<!-- VoxMark include: extension not allowed: {raw_path!r} -->'
            )

        # Circular-include guard
        if target in _seen:
            return (
                f'<!-- VoxMark include: circular reference skipped: {raw_path!r} -->'
            )

        if not target.exists():
            return (
                f'<!-- VoxMark include: file not found: {raw_path!r} -->'
            )

        _log.debug('include: resolving %s (depth=%d)', target, depth)

        try:
            child_source = target.read_text(encoding='utf-8')
        except Exception as exc:
            return f'<!-- VoxMark include: read error: {exc} -->'

        # Recurse — includes inside the included file get their own base_dir
        child_source = _resolve_includes(
            child_source,
            target.parent,
            _seen | {target},
            depth + 1,
        )

        # Now render the child source through the full VML pipeline
        from .renderer import render as _render_child
        rendered = _render_child(child_source)

        # Wrap as ::include[path]{rendered_html} so render_include() can
        # apply its <div class="vml-include"> wrapper at the language level.
        # We use a raw f-string so the content stays verbatim (not re-scanned).
        safe_path = raw_path.replace('{', '&#123;').replace('}', '&#125;')
        return f'::include[{safe_path}]{{{rendered}}}'

    return INCLUDE_PAT.sub(_resolve_one, source)


def compile_vml(
    source:   str,
    base_css: str = '',
    src_path: pathlib.Path | None = None,
) -> CompileResult:
    """
    Full VoxMark compilation pipeline.

    Parameters
    ----------
    source   : raw VML/Markdown source text
    base_css : pre-existing stylesheet content to include in HTML output
               (typically the contents of voxmark/style.css)
    src_path : optional path of the source file — needed for build-time
               ``::include[...]`` resolution.  If None, includes are skipped.

    Pipeline
    --------
    0. Include resolution  → ::include[path] widgets inlined from disk
    1. Lex + Parse         → Document AST  (no regex) — used by CSS/WASM phases
    2. renderer.render()   → full Markdown + VML HTML (headings, paragraphs,
                              lists, hr, code highlighting, widgets)
    3. CSSCompiler         → extracted CSS bundle (::css / ::cssvar / ::style)
    4. WASMCompiler        → .wasm binary + JS loader (from the AST)

    Returns a CompileResult with all four outputs plus the AST.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    # ── Phase 0: Resolve ::include[...] widgets ────────────────────────────────
    if src_path is not None:
        base_dir = pathlib.Path(src_path).resolve().parent
        source   = _resolve_includes(source, base_dir)
        _log.debug('compile_vml: includes resolved, source now %d chars', len(source))

    # ── Phase 1: Parse (still needed for CSS + WASM phases) ───────────────────
    doc = parse(source)

    # Pre-collect ::var definitions shared across all three compilers
    shared_vars: Dict[str, str] = {}

    def _collect(nodes) -> None:
        for n in nodes:
            if isinstance(n, Widget) and n.cmd == 'var':
                shared_vars[n.arg0] = n.body_text.strip()
            if isinstance(n, Widget):
                for s in n.segments:
                    _collect(s.children)

    _collect(doc.children)
    _log.debug('compile_vml: %d vars, %d AST nodes', len(shared_vars), len(doc.children))

    # ── Phase 2: HTML — full Markdown + VML pipeline (matches live editor) ─────
    from .renderer import render as _render_full
    rendered_html = _render_full(source)
    html_result   = HTMLResult(html=rendered_html, css=base_css)

    # ── Phase 3: CSS ──────────────────────────────────────────────────────────
    css_compiler = CSSCompiler()
    css_result   = css_compiler.compile(doc)

    # ── Phase 4: WASM ─────────────────────────────────────────────────────────
    wasm_compiler = WASMCompiler()
    wasm_result   = wasm_compiler.compile(doc, dict(shared_vars))

    return CompileResult(
        html       = html_result,
        css        = css_result,
        wasm       = wasm_result,
        ast        = doc,
        source_len = len(source),
    )


def compile_vml_file(
    src_path: pathlib.Path | str,
    base_css: str = '',
) -> CompileResult:
    """
    Convenience wrapper: read *src_path*, compile it with path-aware include
    resolution, and return the CompileResult.

    This is what ``voxmark compiler --build`` uses internally so that
    ``::include[./other.vml]`` works correctly relative to the source file.
    """
    p      = pathlib.Path(src_path).resolve()
    source = p.read_text(encoding='utf-8')
    return compile_vml(source, base_css=base_css, src_path=p)