"""
VoxMark Renderer — Markdown + VML pipeline.
Author: Divyanshu Sinha

Pipeline (fixed):
  1. Pre-pass: stash ALL VML blocks (preserving them through Markdown)
  2. Run Mistune Markdown on the rest
  3. Restore stashed VML, running Markdown on their BODIES first, then VML transform
  4. Final VML pass for any remaining inline widgets
  5. Var tokens (@name) resolved last using a shared var dict
"""

import re
import html as _html_mod
from typing import List, Tuple
import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from .language import VMLTransformer

# Stash key that survives Markdown (no special MD chars).
# Defined here (before _SyntaxHighlighter) since heading() references it.
_STASH_RE = re.compile(r'VMLSTASH([0-9]+)END')


# ── Mistune renderer ──────────────────────────────────────────────────────────

class _SyntaxHighlighter(mistune.HTMLRenderer):
    """Mistune renderer with Pygments syntax highlighting."""

    def __init__(self, stash: list | None = None) -> None:
        super().__init__()
        # Reference to the renderer's stash list (shared, mutated externally)
        # so heading() can derive a readable slug instead of the raw
        # VMLSTASHxEND placeholder that's present at Mistune-pass time.
        self._stash = stash if stash is not None else []
        self._slug_seen: dict[str, int] = {}

    def codespan(self, code: str) -> str:
        return f'<code class="vml-inline-code">{_html_mod.escape(code)}</code>'

    def block_code(self, code: str, **attrs) -> str:
        info = attrs.get('attrs', {}).get('class', '') or ''
        lang = info.replace('language-', '').strip() if info else ''
        try:
            lexer = get_lexer_by_name(lang) if lang else TextLexer()
        except ClassNotFound:
            lexer = TextLexer()
        formatter = HtmlFormatter(
            cssclass='vml-code-block',
            nowrap=False,
            style='one-dark',
        )
        highlighted = highlight(code, lexer, formatter)
        lang_label = f'<span class="vml-code-lang">{_html_mod.escape(lang)}</span>' if lang else ''
        copy_btn = '<button class="vml-copy-btn" onclick="vmlCopy(this)">Copy</button>'
        return (
            f'<div class="vml-code-wrap">'
            f'<div class="vml-code-toolbar">{lang_label}{copy_btn}</div>'
            f'{highlighted}'
            f'</div>'
        )

    def heading(self, text: str, level: int, **attrs) -> str:
        # Derive slug source from a stripped-down version of the heading text:
        #  - resolve VMLSTASHxEND placeholders to the underlying widget's raw
        #    args/body (so the slug reflects real content, e.g. "buttons" not
        #    "vmlstash1end")
        #  - strip any HTML tags that survived from inline VML widgets
        #  - strip raw ::cmd[..]{..} syntax that may still be present
        slug_source = _STASH_RE.sub(self._stash_preview, text)
        slug_source = re.sub(r'<[^>]+>', '', slug_source)              # strip HTML tags
        slug_source = re.sub(r':{2,3}\w+(?:\[[^\]]*\])?', '', slug_source)  # strip ::cmd[arg]
        slug_source = re.sub(r'[{}]', '', slug_source)                 # strip stray braces

        slug = re.sub(r'[^\w\-]', '', slug_source.lower().replace(' ', '-')).strip('-')
        if not slug:
            slug = f'section-{level}'

        # De-duplicate slugs that collide (e.g. two headings with the same text)
        if slug in self._slug_seen:
            self._slug_seen[slug] += 1
            slug = f'{slug}-{self._slug_seen[slug]}'
        else:
            self._slug_seen[slug] = 0

        anchor = f'<a class="vml-heading-anchor" href="#{slug}">¶</a>'
        return f'<h{level} id="{slug}" class="vml-h{level}">{text}{anchor}</h{level}>\n'

    def _stash_preview(self, m: re.Match) -> str:
        """Best-effort plain-text preview of a stashed VML widget, for slugs only."""
        try:
            idx = int(m.group(1))
            original = self._stash[idx]
        except (ValueError, IndexError):
            return ''
        # Pull out bracketed arg and/or braced body text as a readable fallback
        arg_m  = re.search(r'\[([^\]]*)\]', original)
        body_m = re.search(r'\{(.*)\}', original, re.DOTALL)
        if body_m:
            inner = re.sub(r'::+\w+(?:\[[^\]]*\])?', '', body_m.group(1))
            return re.sub(r'[{}|]', ' ', inner).strip()
        if arg_m:
            return arg_m.group(1).split('|')[0].strip()
        return ''

    def table(self, text: str) -> str:
        return f'<div class="vml-table-wrap"><table class="vml-table">{text}</table></div>'

    def image(self, alt: str, url: str, title: str = '') -> str:
        title_attr = f' title="{_html_mod.escape(title)}"' if title else ''
        return (
            f'<figure class="vml-figure">'
            f'<img src="{_html_mod.escape(url)}" alt="{_html_mod.escape(alt)}"{title_attr} loading="lazy">'
            f'{"<figcaption>" + _html_mod.escape(title) + "</figcaption>" if title else ""}'
            f'</figure>'
        )

    def block_quote(self, text: str) -> str:
        return f'<blockquote class="vml-blockquote">{text}</blockquote>'

    def thematic_break(self) -> str:
        return '<hr class="vml-hr">'


def _make_markdown(stash: list) -> 'mistune.Markdown':
    """Build a fresh Mistune instance bound to this render() call's stash list,
    so heading() can resolve VMLSTASHxEND placeholders into readable slugs."""
    return mistune.create_markdown(
        renderer=_SyntaxHighlighter(stash),
        plugins=['strikethrough', 'table', 'url', 'task_lists'],
    )

# Plain (stash-less) instance used for non-heading-sensitive Markdown work
# (e.g. _md_body on widget body fragments where slugs are less critical).
_md = mistune.create_markdown(
    renderer=_SyntaxHighlighter(),
    plugins=['strikethrough', 'table', 'url', 'task_lists'],
)

# Pattern for the OPENER only — :: or ::: + cmd + optional [arg].
# The body's true extent (matching {...}) is found with a manual brace-depth
# scanner below, since Python `re` cannot do real recursive bracket matching
# and a "one level of nesting" regex breaks on real-world code blocks that
# contain multiple/deeper brace groups (e.g. Rust fn bodies).
_OPENER_PAT = re.compile(r':{2,3}(\w+)(?:\[([^\]]*)\])?')

# Bodyless widgets — args only, never followed by a brace body.
_BODYLESS_CMDS = frozenset({'divider', 'spacer', 'badge', 'progress'})


def _find_matching_brace(text: str, open_idx: int) -> int:
    """
    Given the index of an opening '{' in text, return the index of its
    matching closing '}' using proper depth tracking (handles unlimited
    nesting, unlike a fixed-depth regex).  Returns -1 if unmatched.
    """
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _find_code_zones(source: str) -> List[Tuple[int, int]]:
    """
    Locate every span of source text that is inside a fenced code block
    (``` ... ``` or ~~~ ... ~~~) or an inline code span (`...` / ``...``),
    so the widget scanner can skip VML-looking syntax that the author wrote
    as literal example text (e.g. `` `::var[name]{value}` `` in a callout,
    or `"::alert[...]{...}"` inside a Python string shown in a ```python
    fenced block). Without this, such text gets executed as a real widget
    instead of being displayed as-is.

    Returns a list of (start, end) spans in document order. Fenced blocks
    are matched line-by-line (must start at column 0, optionally indented
    up to 3 spaces per CommonMark); inline spans use the standard
    backtick-run-matching rule (a span of N backticks closes only at the
    next run of exactly N backticks).
    """
    zones: List[Tuple[int, int]] = []

    # ── Fenced code blocks: ``` or ~~~, 3+ characters, same fence to close ──
    fence_pat = re.compile(r'^( {0,3})(`{3,}|~{3,})[^\n]*$', re.MULTILINE)
    pos = 0
    n = len(source)
    while pos < n:
        m = fence_pat.search(source, pos)
        if not m:
            break
        fence_char = m.group(2)[0]
        fence_len  = len(m.group(2))
        indent     = m.group(1)
        open_start = m.start()
        search_from = m.end() + 1  # skip past the opener line's newline
        # Find a closing fence: same indent-or-less, same char, length >= opener
        close_pat = re.compile(
            rf'^ {{0,3}}{re.escape(fence_char)}{{{fence_len},}}[ \t]*$',
            re.MULTILINE,
        )
        cm = close_pat.search(source, search_from)
        if cm:
            zone_end = cm.end()
        else:
            # Unclosed fence — protect to end of document
            zone_end = n
        zones.append((open_start, zone_end))
        pos = zone_end

    # ── Inline code spans: `...`, ``...``, etc. (backtick-run matching) ─────
    i = 0
    while i < n:
        if source[i] == '`':
            # Skip if this position is already inside a fenced block zone
            if any(s <= i < e for s, e in zones):
                i += 1
                continue
            run_start = i
            j = i
            while j < n and source[j] == '`':
                j += 1
            run_len = j - run_start
            # Search for a closing run of exactly run_len backticks
            k = j
            close_start = -1
            while k < n:
                if source[k] == '`':
                    ck = k
                    while ck < n and source[ck] == '`':
                        ck += 1
                    if ck - k == run_len:
                        close_start = k
                        break
                    k = ck
                else:
                    k += 1
            if close_start != -1:
                zones.append((run_start, close_start + run_len))
                i = close_start + run_len
            else:
                # Unmatched backtick run — not a code span, skip past it
                i = j
        else:
            i += 1

    zones.sort()
    return zones


def _in_any_zone(idx: int, zones: List[Tuple[int, int]]) -> bool:
    """True if idx falls within any (start, end) protected zone."""
    for s, e in zones:
        if s <= idx < e:
            return True
        if idx < s:
            break  # zones are sorted by start; no later zone can match
    return False


def _scan_vml_widgets(source: str) -> List[Tuple[int, int, str]]:
    """
    Scan source for all top-level VML widget spans using the opener regex
    plus manual brace-depth matching for the body.

    Widget openers that fall inside a fenced code block or inline code span
    are skipped — that text is example/literal syntax meant to be displayed,
    not executed (e.g. `` `::var[x]{y}` `` in prose, or a Python string
    literal containing `::alert[...]{...}` shown inside a ```python block).

    Returns a list of (start, end, matched_text) tuples in document order.
    Overlapping/nested widgets are NOT separately listed here — a nested
    widget inside a body is captured as part of its parent's raw text and
    re-processed during the body's own Markdown + VML pass.
    """
    spans: List[Tuple[int, int, str]] = []
    code_zones = _find_code_zones(source)
    pos = 0
    n = len(source)

    while pos < n:
        m = _OPENER_PAT.search(source, pos)
        if not m:
            break

        if _in_any_zone(m.start(), code_zones):
            # This '::'/':::' is inside a code block/span — not a real widget.
            # Skip past just the opener so we don't re-match it, but keep
            # scanning the rest of the document normally.
            pos = m.start() + 2
            continue

        cmd = m.group(1).lower()
        after_opener = m.end()

        # Bodyless widget: ::cmd[arg] with no following '{'
        if cmd in _BODYLESS_CMDS and (after_opener >= n or source[after_opener] != '{'):
            spans.append((m.start(), after_opener, source[m.start():after_opener]))
            pos = after_opener
            continue

        # Must be followed immediately by '{' to be a real widget with a body
        if after_opener >= n or source[after_opener] != '{':
            # Not a valid widget opener (e.g. bare '::' in prose) — skip past it
            pos = m.start() + 2
            continue

        close_idx = _find_matching_brace(source, after_opener)
        if close_idx == -1:
            # Unclosed brace — treat opener as plain text, keep scanning past it
            pos = after_opener + 1
            continue

        end = close_idx + 1
        spans.append((m.start(), end, source[m.start():end]))
        pos = end

    return spans


def _md_body(text: str) -> str:
    """Run Markdown on a snippet, strip outer <p>…</p> if single paragraph."""
    result = _md(text.strip())
    # Strip single wrapping <p>…</p> so inline content doesn't add block spacing
    result = result.strip()
    if result.startswith('<p>') and result.endswith('</p>') and result.count('<p>') == 1:
        result = result[3:-4]
    return result


def render(source: str) -> str:
    """
    Full VoxMark render pipeline — all bugs fixed.

    Pass order:
      1. Pre-scan ::var definitions → shared_vars dict
      2. Stash ALL VML widgets (bodyless too) behind VMLSTASHXEND tokens
      3. Run Mistune Markdown on the protected source
      4. Unwrap <p>VMLSTASHXEND</p> → bare VMLSTASHXEND   ← fixes block widget p-wrapping
      5. Restore each stash entry: Markdown the body, then VML-transform
      6. Final VML + @var pass on remaining text
    """
    # ── PASS 1: collect ::var and ::class_def ─────────────────────────────────
    # Uses the same depth-aware scanner so bodies with nested braces are
    # captured correctly.
    shared_vars:    dict[str, str]             = {}
    shared_classes: dict[str, dict[str, str]]  = {}
    for start, end, raw in _scan_vml_widgets(source):
        om = _OPENER_PAT.match(raw)
        if not om or not raw.endswith('}'):
            continue
        wcmd = om.group(1).lower()
        warg = (om.group(2) or '').strip()
        wbody = raw[om.end() + 1 : -1]
        if wcmd == 'var' and warg:
            shared_vars[warg] = wbody.strip()
        elif wcmd == 'class_def' and warg:
            from .language import define_class, _VML_CLASSES
            define_class(warg, wbody)
            safe_name = re.sub(r'[^\w]', '', warg).strip()
            if safe_name in _VML_CLASSES:
                shared_classes[safe_name] = _VML_CLASSES[safe_name]

    # ── PASS 2: stash ALL VML widgets (depth-aware, handles unlimited nesting) ─
    stash: list[str] = []
    spans = _scan_vml_widgets(source)

    if spans:
        pieces: List[str] = []
        cursor = 0
        for start, end, raw in spans:
            pieces.append(source[cursor:start])
            idx = len(stash)
            stash.append(raw)
            pieces.append(f'VMLSTASH{idx}END')
            cursor = end
        pieces.append(source[cursor:])
        protected = ''.join(pieces)
    else:
        protected = source

    # ── PASS 3: Markdown (bound to this call's stash for slug resolution) ──────
    md = _make_markdown(stash)
    html_out = md(protected)

    # ── PASS 4: unwrap block stash keys from <p> tags ─────────────────────────
    # Mistune wraps lone text tokens in <p>. When that token is our stash key
    # for a block widget (div, graph, embed, etc.) the restored HTML ends up
    # invalid inside <p>. Strip the wrapping for <p> that contains ONLY stash keys.
    # Also handles multiple adjacent stash keys merged into one <p> by Mistune.
    _LONE_STASH_IN_P = re.compile(
        r'<p>((?:\s*VMLSTASH\d+END\s*)+)</p>',
        re.DOTALL
    )
    html_out = _LONE_STASH_IN_P.sub(lambda m: m.group(1), html_out)

    # ── PASS 5: restore stash entries ─────────────────────────────────────────
    def _restore(m: re.Match) -> str:
        idx = int(m.group(1))
        original = stash[idx]
        stripped = original.strip()

        t = VMLTransformer()
        t._vars = shared_vars

        # Bodyless widgets (::divider, ::spacer, ::badge, ::progress)
        bodyless_pat = re.compile(r'^::(divider|spacer|badge|progress)(?:\[([^\]]*)\])?$')
        bm = bodyless_pat.match(stripped)
        if bm:
            return t.dispatch_bodyless(bm.group(1), bm.group(2) or '')

        # Parse: colons, cmd, arg, body — using the depth-aware opener match
        # plus brace-span extraction (not a fixed-nesting regex), so widgets
        # whose body contains multiple/deep brace groups (e.g. multi-language
        # code in a ::tab, or nested Rust fn bodies) are handled correctly.
        om = _OPENER_PAT.match(stripped)
        if not om or not stripped.endswith('}') or stripped[om.end():om.end() + 1] != '{':
            return original

        triple = stripped.startswith(':::')
        cmd    = om.group(1)
        arg    = om.group(2) or ''
        body   = stripped[om.end() + 1 : -1]  # strip opener '{' and trailing '}'

        # Commands whose body must NOT go through Markdown (raw code / CSS / data / labels)
        NO_MD_CMDS = {
            'var', 'class_def',                          # variable/class definitions
            'math', 'kbd', 'chart', 'embed',             # raw content
            'css', 'cssplay', 'cssvar',                  # CSS blocks
            'svg', 'demo', 'graphplay', 'graph',         # raw HTML/graph
            'divider', 'spacer',                         # bodyless (no body to process)
            'input', 'checkbox', 'select',               # form labels — not Markdown
            'if', 'else', 'ifelse',                      # control flow
            'router',                                    # uses :: and || as own delimiters
            'footer',                                    # splits on || itself after md per-col
            'include',                                   # already-rendered included HTML
        }

        if cmd.lower() in NO_MD_CMDS:
            rendered_body = body
        elif triple and cmd.lower() in {'sidebar'}:
            # sidebar body uses --- as divider and :: as link separator —
            # must not pass through Markdown or both get destroyed
            rendered_body = body
        elif '||' in body:
            parts = body.split('||')
            rendered_body = '||'.join(_md_body(p) for p in parts)
        else:
            rendered_body = _md_body(body)

        # Dispatch directly using the already-known cmd/arg/body — bypasses
        # transform()'s regex re-matching, which only supports one level of
        # brace nesting and would fail to re-match a rebuilt body containing
        # multiple/deep sibling brace groups (e.g. several <pre> code blocks).
        if triple:
            return t.dispatch_triple(cmd, arg, rendered_body)
        return t.dispatch_double(cmd, arg, rendered_body)

    html_out = _html_mod.unescape(html_out)
    html_out = _STASH_RE.sub(_restore, html_out)

    # ── PASS 6: final inline VML + @var + @Class.prop ─────────────────────────
    t_final = VMLTransformer()
    t_final._vars    = shared_vars
    t_final._classes = shared_classes
    html_out = t_final.transform(html_out)

    return html_out


def get_pygments_css() -> str:
    return HtmlFormatter(style='one-dark', cssclass='vml-code-block').get_style_defs()