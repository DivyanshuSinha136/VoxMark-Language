"""
VoxMark Language (VML) - Custom language extensions for VoxMark.
Author: Divyanshu Sinha
Project: VoxMark

VML Syntax Reference:
  ::card[title]{content}              - Interactive card widget
  ::tab[label1|label2]{c1||c2}        - Tab group
  ::alert[type]{message}              - Alert box (info|warn|error|success)
  ::badge[text|color]                 - Inline badge
  ::progress[value/max|label]         - Progress bar
  ::columns[ratio]{col1||col2}        - Multi-column layout
  ::callout[icon]{text}               - Callout block
  ::kbd{key}                          - Keyboard shortcut display
  ::tooltip[text]{trigger}            - Tooltip on hover
  ::timeline{item1||item2}            - Vertical timeline
  ::math{expression}                  - Inline math (LaTeX-style display)
  ::chart[type]{json-data}            - Mini chart (bar/line/pie/doughnut)
  ::embed[type]{url-or-content}       - Embed media (youtube/image)
  ::var[name]{value}                  - Define a variable (reuse with @name)
  ::if[condition]{content}            - Conditional block (client-side)
  ::color[hex]{text}                  - Colored text span
  ::glow[color]{text}                 - Glowing text effect
  :::fold[title]{content}             - Collapsible fold section
  :::demo{html}                       - Live HTML demo sandbox

  Buttons:
  ::button[style|action]{label}       - Button (primary|secondary|danger|ghost|outline|success)
  :::btngroup{::button[…]||…}         - Button group

  Rich Text:
  ::hl[color]{text}                   - Highlighted/marked text (yellow|green|blue|pink|orange|…)
  ::b[style]{text}                    - Styled bold (gradient|outline|shadow|neon|stamp|underline|strike|mono)

  Icons & SVG:
  ::icon[name|size|color]{fallback}   - Inline SVG icon (30+ icons built-in)
  ::iconcard[icon|title]{desc}        - Icon + title + description card
  :::svg{<svg>…</svg>}                - Raw inline SVG block (sanitized)

  CSS:
  :::css{selector { … }}              - Scoped CSS block (injected into preview only)
  ::style[prop:val; prop:val]{body}   - Inline style wrapper around any content
  ::class[name]{content}              - Apply a custom CSS class to content
  :::cssplay{css||html}               - Live CSS+HTML playground (split editor + live preview)
  ::cssvar[--name]{value}             - Define a CSS custom property for the document scope

  Inputs & Forms:
  ::input[type|placeholder|id]{label} - Styled input field (text|number|email|password|date|range|color|file)
  ::checkbox[id|value]{label}         - Styled checkbox with label
  ::select[id]{opt1|opt2|opt3}        - Styled dropdown select

  Control Flow:
  ::if[condition]{content}            - Show block when JS condition is truthy
  ::else[condition]{content}          - Show block when preceding ::if was falsy (same condition negated)
  ::ifelse[condition]{then||else}     - Inline if/else — two segments split by ||

  Classes (object-style variable namespaces):
  ::class_def[ClassName]{key:val||key2:val2}   - Define a named class with dot-accessible properties
  @ClassName.property                          - Reference a class property anywhere in the document
"""

import re
import json
import html
from typing import Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    return html.escape(str(s))

def _uid() -> str:
    import uuid
    return uuid.uuid4().hex[:8]


# ── individual widget renderers ───────────────────────────────────────────────

def render_card(title: str, content: str) -> str:
    return (
        f'<div class="vml-card">'
        f'<div class="vml-card-title">{_esc(title)}</div>'
        f'<div class="vml-card-body">{content}</div>'
        f'</div>'
    )

def render_tab(labels_raw: str, content_raw: str) -> str:
    uid = _uid()
    labels = [l.strip() for l in labels_raw.split('|')]
    contents = content_raw.split('||')
    tabs_html = ''
    panels_html = ''
    for i, (label, panel) in enumerate(zip(labels, contents)):
        active = 'active' if i == 0 else ''
        tabs_html += (
            f'<button class="vml-tab-btn {active}" '
            f'onclick="vmlTab(\'{uid}\',{i})" id="tb-{uid}-{i}">'
            f'{_esc(label.strip())}</button>'
        )
        panels_html += (
            f'<div class="vml-tab-panel {active}" id="tp-{uid}-{i}">'
            f'{panel.strip()}</div>'
        )
    return (
        f'<div class="vml-tabs" id="tabs-{uid}">'
        f'<div class="vml-tab-bar">{tabs_html}</div>'
        f'<div class="vml-tab-content">{panels_html}</div>'
        f'</div>'
    )

def render_alert(atype: str, message: str) -> str:
    icons = {'info': '●', 'warn': '▲', 'error': '✕', 'success': '✓'}
    icon = icons.get(atype, '●')
    return (
        f'<div class="vml-alert vml-alert-{_esc(atype)}">'
        f'<span class="vml-alert-icon">{icon}</span>'
        f'<span class="vml-alert-msg">{message}</span>'
        f'</div>'
    )

def render_badge(text: str, color: str = '#6c63ff') -> str:
    return f'<span class="vml-badge" style="background:{_esc(color)}">{_esc(text)}</span>'

def render_progress(value: str, maxval: str, label: str = '') -> str:
    try:
        pct = round(float(value) / float(maxval) * 100, 1)
    except Exception:
        pct = 0
    return (
        f'<div class="vml-progress">'
        f'{"<span class=vml-progress-label>" + _esc(label) + "</span>" if label else ""}'
        f'<div class="vml-progress-track">'
        f'<div class="vml-progress-bar" style="width:{pct}%" data-pct="{pct}"></div>'
        f'</div>'
        f'<span class="vml-progress-pct">{pct}%</span>'
        f'</div>'
    )

def render_columns(ratio: str, content_raw: str) -> str:
    cols = content_raw.split('||')
    parts = ratio.split(':') if ':' in ratio else ['1'] * len(cols)
    col_html = ''.join(
        f'<div class="vml-col" style="flex:{p.strip()}">{c.strip()}</div>'
        for p, c in zip(parts, cols)
    )
    return f'<div class="vml-columns">{col_html}</div>'

def render_callout(icon: str, text: str) -> str:
    return (
        f'<div class="vml-callout">'
        f'<span class="vml-callout-icon">{_esc(icon)}</span>'
        f'<div class="vml-callout-text">{text}</div>'
        f'</div>'
    )

def render_kbd(key: str) -> str:
    keys = [k.strip() for k in key.split('+')]
    return ' <span class="vml-kbd-plus">+</span> '.join(
        f'<kbd class="vml-kbd">{_esc(k)}</kbd>' for k in keys
    )

def render_tooltip(tip: str, trigger: str) -> str:
    return (
        f'<span class="vml-tooltip-wrap" tabindex="0">'
        f'{trigger}'
        f'<span class="vml-tooltip-box">{_esc(tip)}</span>'
        f'</span>'
    )

def render_timeline(items_raw: str) -> str:
    items = items_raw.split('||')
    inner = ''
    for item in items:
        item = item.strip()
        # Support "Title::Description" within a timeline entry
        if '::' in item:
            parts = item.split('::', 1)
            inner += (
                f'<div class="vml-timeline-item">'
                f'<div class="vml-timeline-dot"></div>'
                f'<div class="vml-timeline-content">'
                f'<strong>{_esc(parts[0].strip())}</strong>'
                f'<p>{_esc(parts[1].strip())}</p>'
                f'</div></div>'
            )
        else:
            inner += (
                f'<div class="vml-timeline-item">'
                f'<div class="vml-timeline-dot"></div>'
                f'<div class="vml-timeline-content"><p>{_esc(item)}</p></div>'
                f'</div>'
            )
    return f'<div class="vml-timeline">{inner}</div>'

def render_math(expr: str) -> str:
    # Outputs a span that MathJax/KaTeX can pick up, wrapped safely
    return f'<span class="vml-math">\\({_esc(expr)}\\)</span>'

def render_color(hex_color: str, text: str) -> str:
    return f'<span style="color:{_esc(hex_color)}">{text}</span>'

def render_glow(color: str, text: str) -> str:
    return (
        f'<span class="vml-glow" '
        f'style="text-shadow:0 0 8px {_esc(color)},0 0 20px {_esc(color)};'
        f'color:{_esc(color)}">{text}</span>'
    )

def render_fold(title: str, content: str) -> str:
    uid = _uid()
    return (
        f'<details class="vml-fold" id="fold-{uid}">'
        f'<summary class="vml-fold-title">{_esc(title)}</summary>'
        f'<div class="vml-fold-body">{content}</div>'
        f'</details>'
    )

def render_demo(html_src: str) -> str:
    uid = _uid()
    escaped = _esc(html_src)
    return (
        f'<div class="vml-demo">'
        f'<div class="vml-demo-bar">'
        f'<span>Live Demo</span>'
        f'<button class="vml-demo-run" onclick="vmlRunDemo(\'{uid}\')">▶ Run</button>'
        f'</div>'
        f'<div class="vml-demo-split">'
        f'<textarea class="vml-demo-src" id="ds-{uid}" spellcheck="false">{escaped}</textarea>'
        f'<iframe class="vml-demo-frame" id="df-{uid}" sandbox="allow-scripts"></iframe>'
        f'</div>'
        f'</div>'
    )

def render_button(text: str, style: str, action: str) -> str:
    """
    ::button[style|action]{label}
    style: primary | secondary | danger | ghost | outline | success
    action: any URL, #anchor, or JS expression prefixed with js:
    """
    style = (style or 'primary').strip().lower()
    label = text
    if action.startswith('js:'):
        href = '#'
        onclick = f' onclick="{_esc(action[3:])}"'
    elif action.startswith('#') or action.startswith('http'):
        href = _esc(action)
        onclick = ''
    else:
        href = _esc(action) if action else '#'
        onclick = ''
    return (
        f'<a href="{href}"{onclick} class="vml-btn vml-btn-{_esc(style)}">'
        f'{label}</a>'
    )

def render_button_group(items_raw: str) -> str:
    """:::btngroup{::button[primary|#]{A}||::button[ghost|#]{B}}"""
    items = items_raw.split('||')
    inner = ''.join(f'<span class="vml-btngroup-item">{i.strip()}</span>' for i in items)
    return f'<div class="vml-btngroup">{inner}</div>'

def render_highlight(color: str, text: str) -> str:
    """::hl[color]{text} — highlighted/marked text"""
    palette = {
        'yellow': '#fde047', 'green':  '#86efac', 'blue':  '#93c5fd',
        'pink':   '#f9a8d4', 'orange': '#fdba74', 'purple': '#c4b5fd',
        'red':    '#fca5a5', 'cyan':   '#67e8f9',
    }
    bg = palette.get(color.lower(), color if color.startswith('#') else '#fde047')
    # Dark foreground for light highlights
    fg = '#1a1d2e'
    return (
        f'<mark class="vml-hl" style="background:{_esc(bg)};color:{_esc(fg)}">'
        f'{text}</mark>'
    )

def render_bold_styled(style: str, text: str) -> str:
    """
    ::b[style]{text}
    style: gradient | outline | shadow | neon | stamp | underline | strike | mono
    """
    style = style.lower().strip()
    _Style : dict[str | str] = {
        "gradient"  : f'<strong class="vml-b vml-b-gradient">{text}</strong>',
        "outline"   : f'<strong class="vml-b vml-b-outline">{text}</strong>',
        "shadow"    : f'<strong class="vml-b vml-b-shadow">{text}</strong>',
        "neon"      : f'<strong class="vml-b vml-b-neon">{text}</strong>',
        "stamp"     : f'<strong class="vml-b vml-b-stamp">{text}</strong>',
        "underline" : f'<strong class="vml-b vml-b-underline">{text}</strong>',
        "strike"    : f'<s class="vml-b vml-b-strike">{text}</s>',
        "mono"      : f'<strong class="vml-b vml-b-mono">{text}</strong>',
    }

    return _Style.get(style, f'<strong>{text}</strong>')

def render_icon(name: str, size: str = '1em', color: str = '') -> str:
    """
    ::icon[name|size|color]{fallback-emoji}

    Renders an inline SVG icon from the built-in VML icon library (100+ icons).
    All icons are 24×24 viewBox, stroke-based (Feather-icon style).

    Categories
    ----------
    BRAND       : vml, voxmark
    ARROWS      : arrow-right, arrow-left, arrow-up, arrow-down,
                  arrow-up-right, arrow-up-left, chevron-right, chevron-left,
                  chevron-up, chevron-down, chevrons-right, chevrons-left,
                  move, corner-up-right, corner-down-right
    STATUS      : check, check-circle, check-square, x, x-circle, x-square,
                  info, warn, alert-circle, alert-triangle, help-circle,
                  shield, shield-check, shield-off
    MEDIA       : play, pause, stop, skip-back, skip-forward, volume, volume-x,
                  mic, mic-off, camera, camera-off, video, video-off, music,
                  headphones, radio, cast, airplay
    FILES       : file, file-text, file-code, file-image, file-archive, folder,
                  folder-open, folder-plus, save, paperclip, clipboard
    EDITING     : edit, edit-2, edit-3, scissors, crop, rotate-cw, rotate-ccw,
                  maximize, minimize, maximize-2, minimize-2
    SOCIAL      : github, twitter, linkedin, youtube, instagram, facebook,
                  twitch, discord, slack, codepen, gitlab, npm, python, figma
    CODING      : code, code-2, terminal, cpu, server, database, cloud,
                  git-branch, git-commit, git-merge, git-pull-request,
                  package, puzzle, command, hash, function
    UI          : layout, sidebar, menu, grid, list, table, columns,
                  bar-chart, bar-chart-2, pie-chart, trending-up, trending-down,
                  activity, filter, sort, toggle-left, toggle-right,
                  sliders, loader, refresh-cw, refresh-ccw
    COMMUNICATION: mail, mail-open, send, message, message-circle,
                   message-square, phone, phone-call, phone-off
    PEOPLE      : user, users, user-plus, user-minus, user-check, user-x
    NATURE      : sun, moon, cloud-rain, wind, umbrella, anchor, feather
    MISC        : star, heart, bookmark, tag, flag, trophy, gift, coffee,
                  zap, battery, wifi, bluetooth, rss, share, eye, eye-off,
                  globe, map, map-pin, navigation, compass, clock, calendar,
                  shopping-cart, shopping-bag, credit-card, dollar-sign,
                  key, unlock, lock, home, building, tool, wrench,
                  bell, bell-off, thumbs-up, thumbs-down, smile, frown,
                  image, image-off, box, layers, rocket, spacer-icon,
                  minus, plus, plus-circle, copy, trash, search, settings,
                  download, upload, external, link, more-horizontal, more-vertical,
                  dots, print, share-2, log-in, log-out, power

    Usage
    -----
    ::icon[vml|1.4em|#7c6dff]{}            ← VML brand icon
    ::icon[github|1.2em|#fff]{}             ← social
    ::icon[bar-chart|1em|#38d9a9]{}         ← chart
    ::icon[git-branch|1em|#f59e0b]{}        ← coding
    ::icon[discord|1em|#5865f2]{}           ← social
    ::icon[database|1em|currentColor]{}     ← coding
    """
    color_attr = color or 'currentColor'
    s = size or '1em'

    ICONS: dict[str, str] = {

        # ── VML Brand ────────────────────────────────────────────────────────
        # Custom-designed mark: double-colon glyph + angle bracket
        'vml': (
            '<path d="M4 6h2.5L9 14l2.5-8H14" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="M15 6l3.5 9L22 6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
            '<circle cx="2" cy="9" r="1.1" fill="currentColor" stroke="none"/>'
            '<circle cx="2" cy="15" r="1.1" fill="currentColor" stroke="none"/>'
        ),
        # Alternate VoxMark logo-mark: V inside a rounded square
        'voxmark': (
            '<rect x="2" y="2" width="20" height="20" rx="5" ry="5" stroke-width="1.8"/>'
            '<path d="M7 8l5 8 5-8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
        ),

        # ── Arrows ────────────────────────────────────────────────────────────
        'arrow-right':       '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
        'arrow-left':        '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
        'arrow-up':          '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
        'arrow-down':        '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
        'arrow-up-right':    '<polyline points="17 7 17 17 7 17"/><line x1="7" y1="7" x2="17" y2="17"/>',
        'arrow-up-left':     '<polyline points="7 7 7 17 17 17"/><line x1="17" y1="7" x2="7" y2="17"/>',
        'chevron-right':     '<polyline points="9 18 15 12 9 6"/>',
        'chevron-left':      '<polyline points="15 18 9 12 15 6"/>',
        'chevron-up':        '<polyline points="18 15 12 9 6 15"/>',
        'chevron-down':      '<polyline points="6 9 12 15 18 9"/>',
        'chevrons-right':    '<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>',
        'chevrons-left':     '<polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/>',
        'move':              '<polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/>',
        'corner-up-right':   '<polyline points="15 14 20 9 15 4"/><path d="M4 20v-7a4 4 0 0 1 4-4h12"/>',
        'corner-down-right': '<polyline points="15 10 20 15 15 20"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>',

        # ── Status & Feedback ─────────────────────────────────────────────────
        'check':           '<polyline points="20 6 9 17 4 12"/>',
        'check-circle':    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        'check-square':    '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
        'x':               '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
        'x-circle':        '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        'x-square':        '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/>',
        'info':            '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
        'warn':            '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        'alert-circle':    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
        'alert-triangle':  '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        'help-circle':     '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        'shield':          '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        'shield-check':    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
        'shield-off':      '<path d="M19.69 14a6.9 6.9 0 0 0 .31-2V5l-8-3-3.16 1.18"/><path d="M4.73 4.73L4 5v7c0 6 8 10 8 10a20.29 20.29 0 0 0 5.62-4.38"/><line x1="1" y1="1" x2="23" y2="23"/>',

        # ── Media ─────────────────────────────────────────────────────────────
        'play':        '<polygon points="5 3 19 12 5 21 5 3"/>',
        'pause':       '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
        'stop':        '<rect x="4" y="4" width="16" height="16"/>',
        'skip-back':   '<polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5"/>',
        'skip-forward':'<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/>',
        'volume':      '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>',
        'volume-x':    '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>',
        'mic':         '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>',
        'mic-off':     '<line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>',
        'camera':      '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
        'camera-off':  '<line x1="1" y1="1" x2="23" y2="23"/><path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34"/><circle cx="12" cy="13" r="4"/>',
        'video':       '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
        'video-off':   '<path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5.66 0H14a2 2 0 0 1 2 2v3.34l1 1L23 7v10"/><line x1="1" y1="1" x2="23" y2="23"/>',
        'music':       '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
        'headphones':  '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3z"/><path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
        'radio':       '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>',
        'cast':        '<path d="M2 16.1A5 5 0 0 1 5.9 20M2 12.05A9 9 0 0 1 9.95 20M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6"/><line x1="2" y1="20" x2="2.01" y2="20"/>',
        'airplay':     '<path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-2"/><polygon points="12 15 17 21 7 21 12 15"/>',

        # ── Files ─────────────────────────────────────────────────────────────
        'file':         '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
        'file-text':    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        'file-code':    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="10 13 8 15 10 17"/><polyline points="14 13 16 15 14 17"/>',
        'file-image':   '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><circle cx="10" cy="13" r="2"/><polyline points="20 17 15 12 8 19"/>',
        'file-archive': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="11" x2="12" y2="11.01"/><line x1="12" y1="14" x2="12" y2="14.01"/><line x1="12" y1="17" x2="12" y2="21"/>',
        'folder':       '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        'folder-open':  '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><polyline points="2 9 22 9"/>',
        'folder-plus':  '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/>',
        'save':         '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
        'paperclip':    '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
        'clipboard':    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',

        # ── Editing ───────────────────────────────────────────────────────────
        'edit':       '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
        'edit-2':     '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>',
        'edit-3':     '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
        'scissors':   '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>',
        'crop':       '<path d="M6.13 1L6 16a2 2 0 0 0 2 2h15"/><path d="M1 6.13L16 6a2 2 0 0 1 2 2v15"/>',
        'rotate-cw':  '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
        'rotate-ccw': '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
        'maximize':   '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
        'minimize':   '<path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>',
        'maximize-2': '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>',
        'minimize-2': '<polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="10" y1="14" x2="3" y2="21"/><line x1="21" y1="3" x2="14" y2="10"/>',

        # ── Social ────────────────────────────────────────────────────────────
        'github':    '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>',
        'twitter':   '<path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"/>',
        'linkedin':  '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>',
        'youtube':   '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46a2.78 2.78 0 0 0-1.95 1.96A29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58A2.78 2.78 0 0 0 3.41 19.6C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.95A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z"/><polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02"/>',
        'instagram': '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>',
        'facebook':  '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
        'twitch':    '<path d="M21 2H3v16h5v4l4-4h5l4-4V2zm-10 9V7m5 4V7"/>',
        'discord':   '<circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><path d="M7.5 7.5c2-1 7-1 9 0M7.5 16.5c2 1 7 1 9 0"/><path d="M20 3H4a2 2 0 0 0-2 2v12.5L6 21l1.5-1.5H7v-2h10v2h-.5L18 21l4-3.5V5a2 2 0 0 0-2-2z"/>',
        'slack':     '<path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"/><path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/><path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5z"/><path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z"/><path d="M14 14.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5z"/><path d="M15.5 19H14v1.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5-.67-1.5-1.5-1.5z"/><path d="M10 9.5C10 8.67 9.33 8 8.5 8h-5C2.67 8 2 8.67 2 9.5S2.67 11 3.5 11h5c.83 0 1.5-.67 1.5-1.5z"/><path d="M8.5 5H10V3.5C10 2.67 9.33 2 8.5 2S7 2.67 7 3.5 7.67 5 8.5 5z"/>',
        'codepen':   '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/><polyline points="2 15.5 12 8.5 22 15.5"/><line x1="12" y1="2" x2="12" y2="8.5"/>',
        'gitlab':    '<path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"/>',
        'npm':       '<path d="M3 3h18v18H3V3zm1.5 1.5v15h15v-15h-15zm1.5 1.5h12v12H6V6zm1.5 1.5v9h9V7.5H7.5zm1.5 1.5h6v6H9V9zm1.5 1.5v3h3v-3h-3z" stroke="none" fill="currentColor"/>',
        'python':    '<path d="M12 2C6.48 2 5 4.48 5 7v2h7v1H5.5C3.57 10 2 11.57 2 13.5v3C2 18.43 3.57 20 5.5 20H8v-3c0-1.66 1.34-3 3-3h5c1.66 0 3-1.34 3-3V7c0-2.52-1.48-5-7-5zm-1.5 2.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/><path d="M12 22c5.52 0 7-2.48 7-5v-2h-7v-1h6.5c1.93 0 3.5-1.57 3.5-3.5v-3C22 5.57 20.43 4 18.5 4H16v3c0 1.66-1.34 3-3 3H8c-1.66 0-3 1.34-3 3v3c0 2.52 1.48 5 7 5zm1.5-2.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z" stroke="none" fill="currentColor"/>',
        'figma':     '<path d="M5 5.5A3.5 3.5 0 0 1 8.5 2H12v7H8.5A3.5 3.5 0 0 1 5 5.5z"/><path d="M12 2h3.5a3.5 3.5 0 1 1 0 7H12V2z"/><path d="M12 12.5a3.5 3.5 0 1 1 7 0 3.5 3.5 0 1 1-7 0z"/><path d="M5 19.5A3.5 3.5 0 0 1 8.5 16H12v3.5a3.5 3.5 0 1 1-7 0z"/><path d="M5 12.5A3.5 3.5 0 0 1 8.5 9H12v7H8.5A3.5 3.5 0 0 1 5 12.5z"/>',

        # ── Coding & Dev ──────────────────────────────────────────────────────
        'code':              '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
        'code-2':            '<path d="M10 20l4-16"/><polyline points="6 9 2 12 6 15"/><polyline points="18 9 22 12 18 15"/>',
        'terminal':          '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
        'cpu':               '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
        'server':            '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>',
        'database':          '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
        'cloud':             '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
        'git-branch':        '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
        'git-commit':        '<circle cx="12" cy="12" r="4"/><line x1="1.05" y1="12" x2="7" y2="12"/><line x1="17.01" y1="12" x2="22.96" y2="12"/>',
        'git-merge':         '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/>',
        'git-pull-request':  '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>',
        'package':           '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
        'puzzle':            '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
        'command':           '<path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/>',
        'hash':              '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>',
        'function':          '<path d="M17 12H7"/><path d="M7 4c0 4 10 4 10 8s-10 4-10 8"/>',
        'brackets':          '<polyline points="9 17 4 12 9 7"/><polyline points="15 7 20 12 15 17"/>',

        # ── UI Components ─────────────────────────────────────────────────────
        'layout':          '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>',
        'sidebar':         '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>',
        'menu':            '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
        'grid':            '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
        'list':            '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        'table':           '<path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/>',
        'columns':         '<path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7m0-18H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7m0-18v18"/>',
        'bar-chart':       '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
        'bar-chart-2':     '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
        'pie-chart':       '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
        'trending-up':     '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
        'trending-down':   '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
        'activity':        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
        'filter':          '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
        'sort':            '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        'toggle-left':     '<rect x="1" y="5" width="22" height="14" rx="7" ry="7"/><circle cx="8" cy="12" r="3"/>',
        'toggle-right':    '<rect x="1" y="5" width="22" height="14" rx="7" ry="7"/><circle cx="16" cy="12" r="3"/>',
        'sliders':         '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
        'loader':          '<line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>',
        'refresh-cw':      '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
        'refresh-ccw':     '<polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>',
        'more-horizontal': '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
        'more-vertical':   '<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>',
        'dots':            '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',

        # ── Communication ─────────────────────────────────────────────────────
        'mail':            '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        'mail-open':       '<path d="M2 7l10 6L22 7"/><path d="M2 7l10-5 10 5v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7z"/>',
        'send':            '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
        'message':         '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'message-circle':  '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
        'message-square':  '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'phone':           '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.27h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L7.91 8.09A16 16 0 0 0 16 16.09l1.08-.96a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
        'phone-call':      '<path d="M15.05 5A5 5 0 0 1 19 8.95M15.05 1A9 9 0 0 1 23 8.94m-1 7.98v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.27h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L7.91 8.09A16 16 0 0 0 16 16.09l1.08-.96a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
        'phone-off':       '<path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><line x1="23" y1="1" x2="1" y2="23"/>',

        # ── People ────────────────────────────────────────────────────────────
        'user':       '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        'users':      '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        'user-plus':  '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',
        'user-minus': '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="23" y1="11" x2="17" y2="11"/>',
        'user-check': '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/>',
        'user-x':     '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/>',

        # ── Nature & Environment ──────────────────────────────────────────────
        'sun':        '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
        'moon':       '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
        'cloud-rain': '<line x1="16" y1="13" x2="16" y2="21"/><line x1="8" y1="13" x2="8" y2="21"/><line x1="12" y1="15" x2="12" y2="23"/><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/>',
        'wind':       '<path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>',
        'umbrella':   '<polyline points="23 12 22 12 12 1 2 12 1 12"/><path d="M12 1v10"/><path d="M12 23v-1a5 5 0 0 0-5-5H6"/>',
        'anchor':     '<circle cx="12" cy="5" r="3"/><line x1="12" y1="22" x2="12" y2="8"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/>',
        'feather':    '<path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/>',

        # ── Misc / Utility ────────────────────────────────────────────────────
        'star':           '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        'heart':          '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
        'bookmark':       '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
        'tag':            '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
        'flag':           '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
        'trophy':         '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/>',
        'gift':           '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
        'coffee':         '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>',
        'zap':            '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
        'battery':        '<rect x="1" y="6" width="18" height="12" rx="2" ry="2"/><line x1="23" y1="13" x2="23" y2="11"/><line x1="6" y1="10" x2="6" y2="14"/><line x1="9" y1="12" x2="3" y2="12"/>',
        'wifi':           '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>',
        'bluetooth':      '<polyline points="6.5 6.5 17.5 17.5 12 23 12 1 17.5 6.5 6.5 17.5"/>',
        'rss':            '<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>',
        'share':          '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
        'share-2':        '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
        'eye':            '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
        'eye-off':        '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
        'globe':          '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
        'map':            '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>',
        'map-pin':        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
        'navigation':     '<polygon points="3 11 22 2 13 21 11 13 3 11"/>',
        'compass':        '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
        'clock':          '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
        'calendar':       '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
        'shopping-cart':  '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
        'shopping-bag':   '<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
        'credit-card':    '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
        'dollar-sign':    '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
        'key':            '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
        'lock':           '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        'unlock':         '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
        'home':           '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        'building':       '<rect x="1" y="3" width="15" height="18"/><path d="M16 8h4l3 4v7h-7V8z"/><line x1="5" y1="7" x2="5.01" y2="7"/><line x1="5" y1="11" x2="5.01" y2="11"/><line x1="5" y1="15" x2="5.01" y2="15"/><line x1="10" y1="7" x2="10.01" y2="7"/><line x1="10" y1="11" x2="10.01" y2="11"/><line x1="10" y1="15" x2="10.01" y2="15"/>',
        'tool':           '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
        'wrench':         '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
        'bell':           '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
        'bell-off':       '<path d="M13.73 21a2 2 0 0 1-3.46 0"/><path d="M18.63 13A17.89 17.89 0 0 1 18 8"/><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"/><path d="M18 8a6 6 0 0 0-9.33-5"/><line x1="1" y1="1" x2="23" y2="23"/>',
        'thumbs-up':      '<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>',
        'thumbs-down':    '<path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>',
        'smile':          '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
        'frown':          '<circle cx="12" cy="12" r="10"/><path d="M16 16s-1.5-2-4-2-4 2-4 2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
        'image':          '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
        'image-off':      '<line x1="2" y1="2" x2="22" y2="22"/><path d="M10.41 10.41a2 2 0 1 1-2.83-2.83"/><line x1="13.5" y1="13.5" x2="6" y2="21"/><path d="M3 3h1m4 0h13v13m0 4H3V7"/><path d="M21 15l-5-5-3.17 3.17"/>',
        'box':            '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
        'layers':         '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
        'rocket':         '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
        'minus':          '<line x1="5" y1="12" x2="19" y2="12"/>',
        'plus':           '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
        'plus-circle':    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
        'copy':           '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
        'trash':          '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
        'search':         '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
        'settings':       '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        'download':       '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
        'upload':         '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
        'external':       '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
        'link':           '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        'print':          '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
        'log-in':         '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>',
        'log-out':        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
        'power':          '<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>',
    }

    inner_svg = ICONS.get(name.lower(), '')
    if not inner_svg:
        # Unknown icon — square placeholder with name initials
        initials = name[:2].upper()
        inner_svg = (
            f'<rect x="2" y="2" width="20" height="20" rx="4" ry="4" stroke-width="1.5"/>'
            f'<text x="12" y="16" text-anchor="middle" font-size="9" font-weight="700" '
            f'fill="{_esc(color_attr)}" stroke="none">{_esc(initials)}</text>'
        )

    return (
        f'<svg class="vml-icon" width="{_esc(s)}" height="{_esc(s)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{_esc(color_attr)}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" style="vertical-align:middle;display:inline-block">'
        f'{inner_svg}'
        f'</svg>'
    )


    """
    ::icon[name|size|color]{fallback-emoji}
    Renders an inline SVG icon from a built-in library.
    name: arrow-right | check | x | info | warn | star | heart | code |
          copy | download | upload | search | settings | user | home |
          mail | bell | lock | unlock | eye | edit | trash | plus | minus |
          external | github | link | moon | sun | zap | box | layers
    """
    color_attr = color or 'currentColor'
    s = size or '1em'

    ICONS: dict[str, str] = {
        'arrow-right': '<polyline points="9 18 15 12 9 6"/>',
        'arrow-left':  '<polyline points="15 18 9 12 15 6"/>',
        'arrow-up':    '<polyline points="18 15 12 9 6 15"/>',
        'arrow-down':  '<polyline points="6 9 12 15 18 9"/>',
        'check': '<polyline points="20 6 9 17 4 12"/>',
        'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        'x': '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
        'x-circle': '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        'info': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
        'warn': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        'star': '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        'heart': '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
        'code': '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
        'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
        'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
        'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
        'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
        'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        'mail': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        'bell': '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
        'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        'unlock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
        'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
        'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
        'trash': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
        'plus': '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
        'plus-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
        'minus': '<line x1="5" y1="12" x2="19" y2="12"/>',
        'external': '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
        'link': '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        'github': '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>',
        'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
        'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
        'zap': '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
        'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
        'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
        'cpu': '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
        'terminal': '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
        'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
        'rocket': '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    }

    inner_svg = ICONS.get(name.lower(), '')
    if not inner_svg:
        # Unknown icon — render a simple square placeholder
        inner_svg = f'<rect x="3" y="3" width="18" height="18" rx="3" fill="none"/><text x="12" y="16" text-anchor="middle" font-size="10">{_esc(name[:2])}</text>'

    return (
        f'<svg class="vml-icon" width="{_esc(s)}" height="{_esc(s)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{_esc(color_attr)}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" style="vertical-align:middle;display:inline-block">'
        f'{inner_svg}'
        f'</svg>'
    )

def render_svg(code: str) -> str:
    """:::svg{<svg>…</svg>} — raw inline SVG block (sanitized)."""
    # Basic sanitisation: remove script tags and event handlers
    code = re.sub(r'<script[\s\S]*?</script>', '', code, flags=re.I)
    code = re.sub(r'\bon\w+\s*=\s*["\'][^"\']*["\']', '', code, flags=re.I)
    code = re.sub(r'javascript\s*:', '', code, flags=re.I)
    return f'<div class="vml-svg-block">{code}</div>'

def render_svg_icon_card(name: str, title: str, desc: str) -> str:
    """::iconcard[icon-name|title]{description}"""
    icon_html = render_icon(name, '2em')
    return (
        f'<div class="vml-icon-card">'
        f'<div class="vml-icon-card-icon">{icon_html}</div>'
        f'<div class="vml-icon-card-body">'
        f'<div class="vml-icon-card-title">{_esc(title)}</div>'
        f'<div class="vml-icon-card-desc">{desc}</div>'
        f'</div></div>'
    )

# ── CSS widgets ───────────────────────────────────────────────────────────────

_CSS_BLOCKED_PROPS = re.compile(
    r'\b(behavior|expression|-moz-binding|javascript)\b', re.I
)
_CSS_BLOCKED_URL = re.compile(r'url\s*\(\s*(?!["\']?(?:https?://|data:image/))', re.I)


def _sanitize_css(css: str) -> str:
    """Strip JS expressions, dangerous url() calls, and @import."""
    css = _CSS_BLOCKED_PROPS.sub('/*blocked*/', css)
    css = _CSS_BLOCKED_URL.sub('url(/*blocked*/', css)
    css = re.sub(r'@import\b[^;]*;', '/* @import blocked */', css, flags=re.I)
    return css


def _scope_css(css_text: str, scope_id: str) -> str:
    """
    Prefix every top-level selector with #preview so styles only apply
    inside the preview pane and never touch the editor UI.
    Also adds a .vml-scope-{scope_id} secondary prefix so multiple :::css
    blocks don't conflict with each other if needed.
    """
    result = []
    i = 0
    text = css_text.strip()
    while i < len(text):
        brace = text.find('{', i)
        if brace == -1:
            result.append(text[i:])
            break
        selector_part = text[i:brace].strip()
        depth, j = 1, brace + 1
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        body_part = text[brace:j]
        if selector_part.startswith('@'):
            # Pass @keyframes, @media etc. through unchanged
            result.append(f'{selector_part} {body_part}')
        else:
            scoped = ', '.join(
                f'#preview {s.strip()}'
                for s in selector_part.split(',') if s.strip()
            )
            result.append(f'{scoped} {body_part}')
        i = j
    return '\n'.join(result)


# ══════════════════════════════════════════════════════════════════════════════
# INPUTS & FORM CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

# Allowed input types — whitelist prevents XSS via type attribute
_INPUT_TYPES = frozenset({
    'text', 'number', 'email', 'password', 'date', 'datetime-local',
    'time', 'url', 'tel', 'search', 'range', 'color', 'file', 'hidden',
})


def render_input(arg: str, label: str) -> str:
    """
    ::input[type|placeholder|id|default|min|max|step]{Label text}

    Renders a fully styled form input with an optional label.
    All arguments are optional (defaults to type=text).

    Syntax examples:
      ::input[text|Enter name|inp-name]{Full Name}
      ::input[number|0|score|0|0|100|1]{Score}
      ::input[range||brightness|50|0|100]{Brightness}
      ::input[color||accent-color|#7c6dff]{Accent}
      ::input[email|you@example.com]{Email address}
    """
    parts       = [p.strip() for p in arg.split('|')]
    itype       = parts[0].lower() if parts and parts[0] else 'text'
    placeholder = parts[1] if len(parts) > 1 else ''
    iid         = parts[2] if len(parts) > 2 and parts[2] else f'vml-inp-{_uid()}'
    default     = parts[3] if len(parts) > 3 else ''
    imin        = parts[4] if len(parts) > 4 else ''
    imax        = parts[5] if len(parts) > 5 else ''
    step        = parts[6] if len(parts) > 6 else ''

    # Clamp to safe type
    if itype not in _INPUT_TYPES:
        itype = 'text'

    safe_id          = html.escape(re.sub(r'[^\w\-]', '', iid))
    safe_placeholder = html.escape(placeholder)
    safe_default     = html.escape(default)
    safe_label       = label.strip()

    attrs = f'type="{itype}" id="{safe_id}" name="{safe_id}"'
    if safe_placeholder:
        attrs += f' placeholder="{safe_placeholder}"'
    if safe_default:
        attrs += f' value="{safe_default}"'
    if imin:
        attrs += f' min="{html.escape(imin)}"'
    if imax:
        attrs += f' max="{html.escape(imax)}"'
    if step:
        attrs += f' step="{html.escape(step)}"'

    label_html = (
        f'<label class="vml-input-label" for="{safe_id}">{_esc(safe_label)}</label>'
        if safe_label else ''
    )

    # Range gets a live value readout
    if itype == 'range':
        readout_id = f'vml-rv-{safe_id}'
        return (
            f'<div class="vml-input-wrap vml-input-range-wrap">'
            f'{label_html}'
            f'<div class="vml-range-row">'
            f'<input class="vml-input vml-range" {attrs} '
            f'oninput="document.getElementById(\'{readout_id}\').textContent=this.value">'
            f'<span class="vml-range-value" id="{readout_id}">'
            f'{safe_default or imin or "0"}</span>'
            f'</div></div>'
        )

    # Color picker gets a swatch preview
    if itype == 'color':
        return (
            f'<div class="vml-input-wrap vml-input-color-wrap">'
            f'{label_html}'
            f'<div class="vml-color-row">'
            f'<input class="vml-input vml-color-picker" {attrs}>'
            f'<span class="vml-color-label">'
            f'{safe_default or "#000000"}</span>'
            f'</div></div>'
        )

    return (
        f'<div class="vml-input-wrap">'
        f'{label_html}'
        f'<input class="vml-input" {attrs}>'
        f'</div>'
    )


def render_checkbox(arg: str, label: str) -> str:
    """
    ::checkbox[id|value|checked]{Label text}

    Renders a styled checkbox. 'checked' as third arg pre-ticks it.

    Syntax examples:
      ::checkbox[agree|yes]{I agree to the terms}
      ::checkbox[newsletter|yes|checked]{Subscribe to newsletter}
    """
    parts   = [p.strip() for p in arg.split('|')]
    cid     = parts[0] if parts and parts[0] else f'vml-cb-{_uid()}'
    value   = parts[1] if len(parts) > 1 else 'on'
    checked = 'checked' if len(parts) > 2 and parts[2].lower() == 'checked' else ''

    safe_id    = html.escape(re.sub(r'[^\w\-]', '', cid))
    safe_value = html.escape(value)
    safe_label = label.strip()

    return (
        f'<label class="vml-checkbox-wrap" for="{safe_id}">'
        f'<input class="vml-checkbox" type="checkbox" '
        f'id="{safe_id}" name="{safe_id}" value="{safe_value}" {checked}>'
        f'<span class="vml-checkbox-box"></span>'
        f'<span class="vml-checkbox-label">{_esc(safe_label)}</span>'
        f'</label>'
    )


def render_select(arg: str, options_raw: str) -> str:
    """
    ::select[id|default|label]{opt1|opt2|opt3}

    Renders a styled dropdown. Body options are pipe-separated.
    Each option can be 'value:Label text' or just 'Label' (value = label).

    Syntax examples:
      ::select[country|US|Country]{US:United States|UK:United Kingdom|IN:India}
      ::select[size||Shirt size]{S|M|L|XL|XXL}
    """
    parts   = [p.strip() for p in arg.split('|')]
    sid     = parts[0] if parts and parts[0] else f'vml-sel-{_uid()}'
    default = parts[1] if len(parts) > 1 else ''
    label   = parts[2] if len(parts) > 2 else ''

    safe_id    = html.escape(re.sub(r'[^\w\-]', '', sid))
    safe_label = label.strip()

    options_html = ''
    for opt in options_raw.split('|'):
        opt = opt.strip()
        if not opt:
            continue
        if ':' in opt:
            val, txt = opt.split(':', 1)
        else:
            val = txt = opt
        val = html.escape(val.strip())
        txt = html.escape(txt.strip())
        sel = ' selected' if val == html.escape(default) else ''
        options_html += f'<option value="{val}"{sel}>{txt}</option>'

    label_html = (
        f'<label class="vml-select-label" for="{safe_id}">{_esc(safe_label)}</label>'
        if safe_label else ''
    )

    return (
        f'<div class="vml-select-wrap">'
        f'{label_html}'
        f'<div class="vml-select-inner">'
        f'<select class="vml-select" id="{safe_id}" name="{safe_id}">'
        f'{options_html}'
        f'</select>'
        f'<span class="vml-select-arrow">▾</span>'
        f'</div></div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONTROL FLOW  (client-side, evaluated in the browser)
# ══════════════════════════════════════════════════════════════════════════════

def render_if(condition: str, content: str) -> str:
    """
    ::if[condition]{content}

    Shows content only when the JS expression `condition` is truthy at
    page-load time. Condition is sanitized to safe characters only.

    Syntax examples:
      ::if[darkMode]{Only visible in dark mode}
      ::if[screen.width > 768]{Wide-screen content}
    """
    uid = _uid()
    safe_cond = _esc(condition)
    return (
        f'<div class="vml-if" data-cond="{safe_cond}" '
        f'id="vif-{uid}" style="display:none">'
        f'{content}'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  try {{'
        f'    var safe = {json.dumps(condition)}.replace(/[^a-zA-Z0-9_.\\s<>=!&|()]/g,"");'
        f'    if(Function("return ("+safe+")")()) {{'
        f'      document.getElementById("vif-{uid}").style.display="";'
        f'    }}'
        f'  }} catch(e){{}}'
        f'}})();'
        f'</script>'
    )


def render_else(condition: str, content: str) -> str:
    """
    ::else[condition]{content}

    Shows content when condition is FALSY — the logical complement of ::if.
    Use the same condition string as the preceding ::if block.

    Syntax example:
      ::if[user.loggedIn]{Welcome back!}
      ::else[user.loggedIn]{Please log in.}
    """
    uid = _uid()
    safe_cond = _esc(condition)
    return (
        f'<div class="vml-else" data-cond="{safe_cond}" '
        f'id="vel-{uid}" style="display:none">'
        f'{content}'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  try {{'
        f'    var safe = {json.dumps(condition)}.replace(/[^a-zA-Z0-9_.\\s<>=!&|()]/g,"");'
        f'    if(!Function("return ("+safe+")")()) {{'
        f'      document.getElementById("vel-{uid}").style.display="";'
        f'    }}'
        f'  }} catch(e){{'
        f'    document.getElementById("vel-{uid}").style.display="";'
        f'  }}'
        f'}})();'
        f'</script>'
    )


def render_ifelse(condition: str, body: str) -> str:
    """
    ::ifelse[condition]{then-content||else-content}

    Inline if/else — two body segments separated by ||.
    Shows the first segment if condition is truthy, second if falsy.

    Syntax example:
      ::ifelse[window.innerWidth > 600]{Wide layout||Narrow layout}
    """
    parts    = body.split('||', 1)
    then_html = parts[0].strip() if parts else ''
    else_html = parts[1].strip() if len(parts) > 1 else ''
    uid_t    = _uid()
    uid_e    = _uid()
    safe_cond = _esc(condition)

    return (
        f'<span class="vml-if" data-cond="{safe_cond}" '
        f'id="vif-{uid_t}" style="display:none">{then_html}</span>'
        f'<span class="vml-else" data-cond="{safe_cond}" '
        f'id="vel-{uid_e}" style="display:none">{else_html}</span>'
        f'<script>'
        f'(function(){{'
        f'  try {{'
        f'    var safe = {json.dumps(condition)}.replace(/[^a-zA-Z0-9_.\\s<>=!&|()]/g,"");'
        f'    var result = Function("return ("+safe+")")();'
        f'    document.getElementById("vif-{uid_t}").style.display = result ? "" : "none";'
        f'    document.getElementById("vel-{uid_e}").style.display = result ? "none" : "";'
        f'  }} catch(e){{'
        f'    document.getElementById("vel-{uid_e}").style.display="";'
        f'  }}'
        f'}})();'
        f'</script>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLASS SYSTEM  (object-style variable namespaces, e.g. @School.name)
# ══════════════════════════════════════════════════════════════════════════════

# Global registry: { 'ClassName': { 'property': 'value', ... } }
# Populated at render time by ::class_def widgets, consumed by @Name.prop refs.
_VML_CLASSES: dict[str, dict[str, str]] = {}


def define_class(class_name: str, body: str) -> str:
    """
    ::class_def[ClassName]{key:value||key2:value2||...}

    Defines a named class (object-style namespace) whose properties are
    accessible anywhere in the document as @ClassName.property.

    Each property is declared as 'key:value' in a || -separated body.
    Values may span the entire text after the first colon.

    Syntax example:
      ::class_def[School]{
        name:Springfield Elementary
        ||address:742 Evergreen Terrace, Springfield
        ||founded:1953
        ||principal:Principal Skinner
      }

    Usage:
      The school is **@School.name**, located at @School.address.
      Founded in @School.founded by @School.principal.

    Notes:
      - ClassName must start with a capital letter (convention, not enforced).
      - Properties are case-sensitive.
      - Re-defining a class replaces all its previous properties.
      - Outputs an invisible <meta> tag for traceability; no visible HTML.
    """
    safe_name = re.sub(r'[^\w]', '', class_name).strip()
    if not safe_name:
        return ''

    props: dict[str, str] = {}
    for segment in body.split('||'):
        segment = segment.strip()
        if not segment:
            continue
        # Split on first ':' only — value may contain colons (URLs, times, etc.)
        if ':' in segment:
            key, _, val = segment.partition(':')
            key = key.strip()
            val = val.strip()
            if key:
                props[key] = val

    _VML_CLASSES[safe_name] = props

    # Emit an invisible anchor so browser dev-tools/search can find definitions
    prop_list = ', '.join(f'{k}' for k in props)
    return (
        f'<meta class="vml-class-def" data-class="{html.escape(safe_name)}" '
        f'data-props="{html.escape(prop_list)}" style="display:none">'
    )


def resolve_class_refs(text: str, classes: dict[str, dict[str, str]]) -> str:
    """
    Replace all @ClassName.property references in text with their values.

    Pattern: @Word.word  (ClassName starts with letter, property is [\\w]+)
    Unknown classes or properties are left as-is (@ClassName.prop unchanged).
    """
    CLASS_REF_PAT = re.compile(r'@([A-Za-z]\w*)\.(\w+)')

    def _replace(m: re.Match) -> str:
        cname = m.group(1)
        prop  = m.group(2)
        cls   = classes.get(cname)
        if cls is None:
            return m.group(0)   # unknown class — leave
        val = cls.get(prop)
        if val is None:
            return m.group(0)   # unknown property — leave
        return val

    return CLASS_REF_PAT.sub(_replace, text)


def render_css_block(css_raw: str, scope_id: str) -> str:
    """
    :::css{selector { … }}
    Injects CSS into the preview. Selectors are prefixed with #preview so
    styles only affect preview content and never leak into the editor UI.
    """
    safe = _sanitize_css(css_raw)
    # Scope to #preview so styles never bleed into the editor
    scoped = _scope_css(safe, scope_id)
    return (
        f'<style id="vml-css-{scope_id}">{scoped}</style>'
        f'<div class="vml-css-block-info">'
        f'<span class="vml-css-block-tag">CSS</span>'
        f'<span class="vml-css-block-label">Scoped stylesheet active</span>'
        f'</div>'
        # Invisible anchor div that carries the scope attribute —
        # all siblings after this point are inside #preview which already
        # matches the scoped selector prefix
        f'<div class="vml-css-scope" data-css-scope="{scope_id}"></div>'
    )


def render_style_wrapper(style_str: str, content: str) -> str:
    """::style[prop:val; prop:val]{content} — inline style applied to content."""
    safe = html.escape(_sanitize_css(style_str))
    tag  = 'div' if re.search(r'<(div|p|h[1-6]|ul|ol|table|blockquote)', content) else 'span'
    return f'<{tag} class="vml-styled" style="{safe}">{content}</{tag}>'


def render_css_class(classname: str, content: str) -> str:
    """::class[name]{content} — apply custom class(es) to content."""
    safe_class = html.escape(re.sub(r'[^\w\s\-]', '', classname))
    tag = 'div' if re.search(r'<(div|p|h[1-6]|ul|ol|table|blockquote)', content) else 'span'
    return f'<{tag} class="vml-custom {safe_class}">{content}</{tag}>'


def render_css_var(name: str, value: str) -> str:
    """::cssvar[--name]{value} — define a CSS custom property in :root scope."""
    safe_name  = re.sub(r'[^\w\-]', '', name)
    safe_value = html.escape(_sanitize_css(value))
    if not safe_name.startswith('--'):
        safe_name = '--' + safe_name
    return f'<style data-vml-cssvar>:root {{ {safe_name}: {safe_value}; }}</style>'


def render_cssplay(content_raw: str) -> str:
    """
    :::cssplay{css code||html code}
    Live CSS+HTML playground — CodePen-style split editor with instant preview.
    All JS functions are instance-local inside an IIFE — multiple playgrounds
    on the same page all work independently.
    """
    parts    = content_raw.split('||', 1)
    css_src  = parts[0].strip() if parts else ''
    html_src = parts[1].strip() if len(parts) > 1 else '<div class="box">Edit me!</div>'
    uid      = _uid()
    esc_css  = html.escape(css_src)
    esc_html = html.escape(html_src)

    # Build HTML structure
    html_part = (
        f'<div class="vml-cssplay" id="cp-{uid}">'
        f'<div class="vml-cssplay-bar">'
        f'<span class="vml-cssplay-title">'
        f'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        f'<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'
        f'</svg> CSS Playground</span>'
        f'<div class="vml-cssplay-tabs" id="cptabs-{uid}">'
        f'<button class="vml-cssplay-tab active" data-cp="{uid}" data-tab="css" onclick="window._cp_{uid}.tab(this,\'css\')">CSS</button>'
        f'<button class="vml-cssplay-tab" data-cp="{uid}" data-tab="html" onclick="window._cp_{uid}.tab(this,\'html\')">HTML</button>'
        f'<button class="vml-cssplay-tab" data-cp="{uid}" data-tab="split" onclick="window._cp_{uid}.tab(this,\'split\')">Split</button>'
        f'</div>'
        f'<div style="display:flex;gap:6px;align-items:center;margin-left:auto">'
        f'<label class="vml-cssplay-bg-toggle">'
        f'<input type="checkbox" id="cpbg-{uid}" onchange="window._cp_{uid}.run()"> Dark bg'
        f'</label>'
        f'<button class="vml-cssplay-run" onclick="window._cp_{uid}.run()">▶ Run</button>'
        f'<button class="vml-cssplay-copy" onclick="window._cp_{uid}.copy()">⎘ Copy</button>'
        f'</div></div>'
        # Editors
        f'<div class="vml-cssplay-editors" id="cpe-{uid}">'
        f'<div class="vml-cssplay-editor-wrap" id="cpew-css-{uid}">'
        f'<div class="vml-cssplay-editor-label">'
        f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#7c6dff" stroke-width="2">'
        f'<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>'
        f'<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'
        f'</svg> CSS</div>'
        f'<textarea class="vml-cssplay-editor" id="cpcss-{uid}" spellcheck="false">{esc_css}</textarea>'
        f'</div>'
        f'<div class="vml-cssplay-editor-wrap" id="cpew-html-{uid}" style="display:none">'
        f'<div class="vml-cssplay-editor-label">'
        f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#38d9a9" stroke-width="2">'
        f'<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'
        f'</svg> HTML</div>'
        f'<textarea class="vml-cssplay-editor" id="cphtml-{uid}" spellcheck="false">{esc_html}</textarea>'
        f'</div>'
        f'</div>'
        # Preview
        f'<div class="vml-cssplay-preview-wrap">'
        f'<div class="vml-cssplay-preview-bar">'
        f'<svg width="8" height="8" viewBox="0 0 8 8"><circle cx="4" cy="4" r="4" fill="#22c55e"/></svg>'
        f' Live Preview'
        f'</div>'
        f'<iframe class="vml-cssplay-preview" id="cpframe-{uid}" sandbox="allow-scripts"></iframe>'
        f'</div>'
        f'</div>'
    )

    # Build JS — all functions stored on window._cp_{uid} object
    # so multiple playgrounds never collide
    js_part = (
        f'<script>'
        f'(function(){{'
        f'var U="{uid}";'
        f'function g(id){{return document.getElementById(id);}}'
        f'function run(){{'
        f'  var css=g("cpcss-"+U)?g("cpcss-"+U).value:"";'
        f'  var htm=g("cphtml-"+U)?g("cphtml-"+U).value:"";'
        f'  var dark=g("cpbg-"+U)?g("cpbg-"+U).checked:false;'
        f'  var bg=dark?"#0d0f18":"#ffffff";'
        f'  var fg=dark?"#e8eaf6":"#111111";'
        f'  var frame=g("cpframe-"+U);'
        f'  if(!frame)return;'
        f'  frame.srcdoc='
        f'    "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\">"'
        f'    +"<style>*{{box-sizing:border-box;margin:0;padding:0}}"'
        f'    +"body{{padding:20px;font-family:system-ui,sans-serif;background:"+bg+";color:"+fg+"}}"'
        f'    +css'
        f'    +"</style></head><body>"+htm+"</body></html>";'
        f'}}'
        f'function tab(btn,t){{'
        f'  var cw=g("cpew-css-"+U);'
        f'  var hw=g("cpew-html-"+U);'
        f'  var ed=g("cpe-"+U);'
        f'  if(t==="css"){{'
        f'    if(cw)cw.style.display="";'
        f'    if(hw)hw.style.display="none";'
        f'    if(ed)ed.style.gridTemplateColumns="1fr";'
        f'  }}else if(t==="html"){{'
        f'    if(cw)cw.style.display="none";'
        f'    if(hw)hw.style.display="";'
        f'    if(ed)ed.style.gridTemplateColumns="1fr";'
        f'  }}else{{'
        f'    if(cw)cw.style.display="";'
        f'    if(hw)hw.style.display="";'
        f'    if(ed)ed.style.gridTemplateColumns="1fr 1fr";'
        f'  }}'
        f'  var tabs=document.querySelectorAll("#cptabs-"+U+" .vml-cssplay-tab");'
        f'  tabs.forEach(function(b){{b.classList.remove("active");}});'
        f'  if(btn)btn.classList.add("active");'
        f'}}'
        # copy(): copy css+html to clipboard
        f'function copy(){{'
        f'  var css=g("cpcss-"+U)?g("cpcss-"+U).value:"";'
        f'  var htm=g("cphtml-"+U)?g("cphtml-"+U).value:"";'
        f'  if(navigator.clipboard){{'
        f'    navigator.clipboard.writeText("<style>\\n"+css+"\\n</style>\\n"+htm);'
        f'  }}'
        f'}}'
        # Register on window so onclick attributes can reach them
        f'window["_cp_"+U]={{run:run,tab:tab,copy:copy}};'
        # Live update on keystroke
        f'["cpcss-"+U,"cphtml-"+U].forEach(function(id){{'
        f'  var el=g(id);'
        f'  if(el)el.addEventListener("input",run);'
        f'}});'
        # Initial render after DOM settles
        f'setTimeout(run,100);'
        f'}})();'
        f'</script>'
    )

    return html_part + js_part


# ══════════════════════════════════════════════════════════════════════════════
# DIV / LAYOUT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def render_div(arg: str, content: str) -> str:
    """
    :::div[class|id|style]{content}
    General purpose block container. Args pipe-separated:
      class  → CSS class(es)
      id     → element id
      style  → inline CSS
    """
    parts  = [p.strip() for p in arg.split('|')]
    cls    = html.escape(re.sub(r'[^\w\s\-]', '', parts[0])) if len(parts) > 0 and parts[0] else ''
    eid    = html.escape(re.sub(r'[^\w\-]', '', parts[1]))   if len(parts) > 1 and parts[1] else ''
    style  = html.escape(_sanitize_css(parts[2]))             if len(parts) > 2 and parts[2] else ''
    attrs  = ''
    if cls:   attrs += f' class="vml-div {cls}"'
    else:     attrs += ' class="vml-div"'
    if eid:   attrs += f' id="{eid}"'
    if style: attrs += f' style="{style}"'
    return f'<div{attrs}>{content}</div>'


def render_box(variant: str, content: str) -> str:
    """
    :::box[variant]{content}
    Variants: default | raised | inset | glass | gradient | outline | dark | light
    """
    v = (variant or 'default').lower().strip()
    return f'<div class="vml-box vml-box-{_esc(v)}">{content}</div>'


def render_hero(arg: str, content: str) -> str:
    """
    :::hero[bg-color|text-align|min-height]{content}
    Full-width hero section block.
    """
    parts  = [p.strip() for p in arg.split('|')]
    bg     = _sanitize_css(parts[0]) if parts and parts[0] else ''
    align  = parts[1] if len(parts) > 1 and parts[1] in ('left','center','right') else 'center'
    height = _sanitize_css(parts[2]) if len(parts) > 2 and parts[2] else '240px'
    style  = f'min-height:{html.escape(height)};text-align:{align};'
    if bg:
        # Accept hex, named colors, or gradient keywords
        if bg.startswith('grad-'):
            presets = {
                'grad-purple': 'linear-gradient(135deg,#7c6dff,#9d50ff)',
                'grad-teal':   'linear-gradient(135deg,#38d9a9,#3b82f6)',
                'grad-sunset': 'linear-gradient(135deg,#f59e0b,#ef4444)',
                'grad-night':  'linear-gradient(135deg,#0d0f18,#252a44)',
                'grad-ocean':  'linear-gradient(135deg,#1e3a5f,#38d9a9)',
                'grad-fire':   'linear-gradient(135deg,#f59e0b,#ef4444,#7c3aed)',
            }
            bg_css = presets.get(bg, 'linear-gradient(135deg,#7c6dff,#9d50ff)')
            style += f'background:{html.escape(bg_css)};'
        else:
            style += f'background:{html.escape(bg)};'
    return f'<div class="vml-hero" style="{style}">{content}</div>'


def render_grid(arg: str, content: str) -> str:
    """
    :::grid[cols|gap]{cell1||cell2||cell3}
    CSS Grid layout. cols = number or template e.g. "3" or "1fr 2fr 1fr"
    """
    parts = [p.strip() for p in arg.split('|')]
    cols_raw = parts[0] if parts and parts[0] else '3'
    gap      = _sanitize_css(parts[1]) if len(parts) > 1 and parts[1] else '16px'
    # cols_raw is either a number or a fr template
    if re.match(r'^\d+$', cols_raw):
        cols_css = f'repeat({cols_raw}, 1fr)'
    else:
        cols_css = html.escape(_sanitize_css(cols_raw))
    cells    = content.split('||')
    cells_html = ''.join(f'<div class="vml-grid-cell">{c.strip()}</div>' for c in cells)
    return (
        f'<div class="vml-grid" '
        f'style="grid-template-columns:{cols_css};gap:{html.escape(gap)}">'
        f'{cells_html}</div>'
    )


def render_flex(arg: str, content: str) -> str:
    """
    :::flex[gap|align|justify|wrap]{item1||item2}
    Flexbox row layout.
    """
    parts   = [p.strip() for p in arg.split('|')]
    gap     = _sanitize_css(parts[0]) if parts and parts[0] else '12px'
    align   = _sanitize_css(parts[1]) if len(parts) > 1 and parts[1] else 'center'
    justify = _sanitize_css(parts[2]) if len(parts) > 2 and parts[2] else 'flex-start'
    wrap    = 'wrap' if len(parts) > 3 and parts[3] == 'wrap' else 'nowrap'
    items   = content.split('||')
    items_html = ''.join(f'<div class="vml-flex-item">{i.strip()}</div>' for i in items)
    return (
        f'<div class="vml-flex" '
        f'style="gap:{html.escape(gap)};align-items:{html.escape(align)};'
        f'justify-content:{html.escape(justify)};flex-wrap:{wrap}">'
        f'{items_html}</div>'
    )


def render_section(arg: str, content: str) -> str:
    """
    :::section[title|subtitle|align]{content}
    Titled document section with optional subtitle.
    """
    parts    = [p.strip() for p in arg.split('|')]
    title    = _esc(parts[0]) if parts and parts[0] else ''
    subtitle = _esc(parts[1]) if len(parts) > 1 and parts[1] else ''
    align    = parts[2] if len(parts) > 2 and parts[2] in ('left','center','right') else 'left'
    header   = ''
    if title:
        header += f'<div class="vml-section-title">{title}</div>'
    if subtitle:
        header += f'<div class="vml-section-subtitle">{subtitle}</div>'
    return (
        f'<section class="vml-section" style="text-align:{align}">'
        f'{"<div class=vml-section-header>" + header + "</div>" if header else ""}'
        f'<div class="vml-section-body">{content}</div>'
        f'</section>'
    )


def render_divider(style: str = 'solid') -> str:
    """::divider[style] — styled horizontal rule. style: solid|dashed|dotted|gradient|dots|stars"""
    s = (style or 'solid').lower().strip()
    if s == 'gradient':
        return '<div class="vml-divider vml-divider-gradient"></div>'
    if s == 'dots':
        return '<div class="vml-divider vml-divider-dots">· · · · · · · · · ·</div>'
    if s == 'stars':
        return '<div class="vml-divider vml-divider-stars">✦ · ✦ · ✦</div>'
    return f'<hr class="vml-divider vml-divider-{_esc(s)}">'


def render_spacer(size: str = '24px') -> str:
    """::spacer[size] — vertical whitespace block."""
    safe = html.escape(_sanitize_css(size or '24px'))
    return f'<div class="vml-spacer" style="height:{safe};display:block"></div>'


def render_center(content: str) -> str:
    """::center{content} — center-align block."""
    return f'<div class="vml-center">{content}</div>'


def render_right(content: str) -> str:
    """::right{content} — right-align block."""
    return f'<div class="vml-right">{content}</div>'


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH SYSTEM  (rich Chart.js integration)
# ══════════════════════════════════════════════════════════════════════════════

# Default color palettes
_GRAPH_PALETTES = {
    'voxmark': ['#7c6dff','#38d9a9','#f59e0b','#ef4444','#3b82f6','#22c55e','#a855f7','#f97316'],
    'pastel':  ['#a5b4fc','#6ee7b7','#fde68a','#fca5a5','#93c5fd','#86efac','#d8b4fe','#fdba74'],
    'mono':    ['#e8eaf6','#9ea3c0','#5c627a','#252a44','#13162a','#0d0f18','#7c6dff','#38d9a9'],
    'neon':    ['#ff00ff','#00ffff','#ffff00','#ff0040','#00ff80','#8000ff','#ff8000','#0080ff'],
    'earth':   ['#92400e','#b45309','#d97706','#65a30d','#15803d','#0369a1','#1d4ed8','#6d28d9'],
}


def _build_graph_data(raw_json: str, chart_type: str, palette: str) -> dict:
    """Parse user JSON and inject VoxMark defaults."""
    try:
        data = json.loads(raw_json.strip())
    except Exception:
        return {}

    colors = _GRAPH_PALETTES.get(palette, _GRAPH_PALETTES['voxmark'])

    # If user gave simple {labels, data} shorthand, expand to full Chart.js format
    if 'labels' in data and 'data' in data and 'datasets' not in data:
        vals = data['data']
        label = data.get('label', 'Data')
        if chart_type in ('pie', 'doughnut', 'polarArea'):
            bg = colors[:len(vals)]
            data = {
                'labels': data['labels'],
                'datasets': [{'label': label, 'data': vals,
                              'backgroundColor': bg,
                              'borderColor': ['#0d0f18'] * len(vals),
                              'borderWidth': 2}]
            }
        else:
            data = {
                'labels': data['labels'],
                'datasets': [{'label': label, 'data': vals,
                              'backgroundColor': colors[0] + '55',
                              'borderColor': colors[0],
                              'borderWidth': 2,
                              'fill': chart_type == 'line',
                              'tension': 0.4,
                              'pointBackgroundColor': colors[0]}]
            }

    # Multi-dataset shorthand: {labels, datasets: [{label, data}, ...]}
    elif 'datasets' in data:
        for i, ds in enumerate(data.get('datasets', [])):
            c = colors[i % len(colors)]
            if 'backgroundColor' not in ds:
                if chart_type in ('pie', 'doughnut', 'polarArea'):
                    ds['backgroundColor'] = colors[:len(ds.get('data', []))]
                else:
                    ds['backgroundColor'] = c + '44'
            if 'borderColor' not in ds:
                ds['borderColor'] = c
            if 'borderWidth' not in ds:
                ds['borderWidth'] = 2
            if chart_type == 'line':
                ds.setdefault('tension', 0.4)
                ds.setdefault('fill', False)
                ds.setdefault('pointBackgroundColor', c)
                ds.setdefault('pointRadius', 4)

    return data


def render_graph(arg: str, raw_json: str) -> str:
    """
    ::graph[type|title|palette|height]{json-data}

    type:    bar | line | pie | doughnut | radar | polar | scatter | bubble | area
    title:   optional chart title
    palette: voxmark(default) | pastel | mono | neon | earth
    height:  canvas height in px (default 280)

    Shorthand JSON:
      {"labels":["A","B","C"], "data":[10,20,30], "label":"Series"}
    Full Chart.js datasets also accepted.
    """
    parts   = [p.strip() for p in arg.split('|')]
    ctype   = parts[0].lower() if parts and parts[0] else 'bar'
    title   = parts[1] if len(parts) > 1 and parts[1] else ''
    palette = parts[2] if len(parts) > 2 and parts[2] else 'voxmark'
    height  = parts[3] if len(parts) > 3 and parts[3] else '280'

    # 'area' is just a filled line
    actual_type = 'line' if ctype == 'area' else ctype
    if ctype == 'area':
        # Inject fill into data
        try:
            tmp = json.loads(raw_json.strip())
            if 'datasets' not in tmp and 'data' in tmp:
                pass  # _build_graph_data handles fill
            elif 'datasets' in tmp:
                for ds in tmp.get('datasets', []):
                    ds['fill'] = True
            raw_json = json.dumps(tmp)
        except Exception:
            pass

    chart_data = _build_graph_data(raw_json, actual_type, palette)
    if not chart_data:
        return f'<div class="vml-error">graph: invalid JSON — {html.escape(raw_json[:80])}</div>'

    uid = _uid()

    # Chart.js options
    is_circular = actual_type in ('pie', 'doughnut', 'polarArea')
    options = {
        'responsive': True,
        'maintainAspectRatio': False,
        'animation': {'duration': 800, 'easing': 'easeInOutQuart'},
        'plugins': {
            'legend': {
                'display': True,
                'position': 'bottom',
                'labels': {'color': '#9ea3c0', 'padding': 16, 'font': {'family': 'Space Grotesk, system-ui', 'size': 12}},
            },
            'title': {
                'display': bool(title),
                'text': title,
                'color': '#e8eaf6',
                'font': {'family': 'Space Grotesk, system-ui', 'size': 15, 'weight': '700'},
                'padding': {'bottom': 12},
            },
            'tooltip': {
                'backgroundColor': '#1e2238',
                'titleColor': '#e8eaf6',
                'bodyColor': '#9ea3c0',
                'borderColor': '#252a44',
                'borderWidth': 1,
                'cornerRadius': 8,
                'padding': 10,
            },
        },
    }
    if not is_circular:
        options['scales'] = {
            'x': {
                'ticks': {'color': '#9ea3c0', 'font': {'family': 'Space Grotesk, system-ui', 'size': 11}},
                'grid':  {'color': '#252a44', 'drawBorder': False},
            },
            'y': {
                'ticks': {'color': '#9ea3c0', 'font': {'family': 'Space Grotesk, system-ui', 'size': 11}},
                'grid':  {'color': '#252a44', 'drawBorder': False},
                'beginAtZero': True,
            },
        }
    if actual_type == 'radar':
        options['scales'] = {
            'r': {
                'ticks': {'color': '#9ea3c0', 'backdropColor': 'transparent'},
                'grid':  {'color': '#252a44'},
                'pointLabels': {'color': '#9ea3c0', 'font': {'size': 12}},
            }
        }

    payload = json.dumps({'type': actual_type, 'data': chart_data, 'options': options})

    return (
        f'<div class="vml-graph-wrap" id="gwrap-{uid}">'
        f'<div style="position:relative;height:{html.escape(height)}px">'
        f'<canvas id="vg-{uid}" class="vml-graph"></canvas>'
        f'</div>'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  var payload={payload};'
        f'  function tryRender(){{'
        f'    var el=document.getElementById("vg-{uid}");'
        f'    if(!el)return;'
        f'    if(typeof Chart==="undefined"){{'
        f'      setTimeout(tryRender,50);return;'
        f'    }}'
        f'    new Chart(el,payload);'
        f'  }}'
        f'  if(document.readyState==="loading"){{'
        f'    document.addEventListener("DOMContentLoaded",tryRender);'
        f'  }}else{{tryRender();}}'
        f'}})();'
        f'</script>'
    )


def render_graphplay(raw: str) -> str:
    """
    :::graphplay{json}
    Live graph editor — edit JSON on the left, see chart on the right, update on every keystroke.
    """
    default_json = raw.strip() or json.dumps({
        'type': 'bar',
        'data': {
            'labels': ['Jan','Feb','Mar','Apr','May','Jun'],
            'datasets': [{'label':'Revenue','data':[12,19,8,25,17,22]}]
        }
    }, indent=2)

    uid      = _uid()
    esc_json = html.escape(default_json)

    return (
        f'<div class="vml-graphplay" id="gp-{uid}">'
        f'<div class="vml-graphplay-bar">'
        f'<span class="vml-graphplay-title">'
        f'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
        f' Graph Playground</span>'
        f'<button class="vml-graphplay-run" onclick="window._gp_{uid}.run()">▶ Render</button>'
        f'<button class="vml-cssplay-copy" onclick="window._gp_{uid}.copy()" style="font-size:12px;padding:4px 10px">⎘ Copy</button>'
        f'</div>'
        f'<div class="vml-graphplay-body">'
        f'<div class="vml-graphplay-editor-wrap">'
        f'<div class="vml-cssplay-editor-label">Chart.js JSON</div>'
        f'<textarea class="vml-cssplay-editor vml-graphplay-editor" id="gpjson-{uid}" spellcheck="false">{esc_json}</textarea>'
        f'</div>'
        f'<div class="vml-graphplay-preview">'
        f'<div style="position:relative;height:260px;width:100%">'
        f'<canvas id="gpc-{uid}"></canvas>'
        f'</div>'
        f'<div class="vml-graphplay-error" id="gperr-{uid}" style="display:none"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  var U="{uid}";'
        f'  var chart=null;'
        f'  function g(id){{return document.getElementById(id);}}'
        f'  function run(){{'
        f'    var raw=g("gpjson-"+U)?g("gpjson-"+U).value:"";'
        f'    var errEl=g("gperr-"+U);'
        f'    if(typeof Chart==="undefined"){{'
        f'      setTimeout(run,50);return;'
        f'    }}'
        f'    try{{'
        f'      var cfg=JSON.parse(raw);'
        f'      if(errEl){{errEl.style.display="none";errEl.textContent="";}}'
        f'      var canvas=g("gpc-"+U);'
        f'      if(!canvas||typeof Chart==="undefined")return;'
        f'      if(chart){{chart.destroy();chart=null;}}'
        # Inject default styling
        f'      var palette=["#7c6dff","#38d9a9","#f59e0b","#ef4444","#3b82f6","#22c55e"];'
        f'      if(cfg.data&&cfg.data.datasets){{'
        f'        cfg.data.datasets.forEach(function(ds,i){{'
        f'          var c=palette[i%palette.length];'
        f'          if(!ds.backgroundColor)ds.backgroundColor=c+"44";'
        f'          if(!ds.borderColor)ds.borderColor=c;'
        f'          if(!ds.borderWidth)ds.borderWidth=2;'
        f'        }});'
        f'      }}'
        f'      if(!cfg.options)cfg.options={{}};'
        f'      if(!cfg.options.plugins)cfg.options.plugins={{}};'
        f'      if(!cfg.options.plugins.legend)cfg.options.plugins.legend={{labels:{{color:"#9ea3c0"}}}};'
        f'      cfg.options.responsive=true;cfg.options.maintainAspectRatio=false;'
        f'      if(!cfg.options.scales&&cfg.type!=="pie"&&cfg.type!=="doughnut"&&cfg.type!=="polarArea"){{'
        f'        cfg.options.scales={{'
        f'          x:{{ticks:{{color:"#9ea3c0"}},grid:{{color:"#252a44"}}}},'
        f'          y:{{ticks:{{color:"#9ea3c0"}},grid:{{color:"#252a44"}},beginAtZero:true}}'
        f'        }};'
        f'      }}'
        f'      chart=new Chart(canvas,cfg);'
        f'    }}catch(e){{'
        f'      if(errEl){{errEl.style.display="block";errEl.textContent="JSON Error: "+e.message;}}'
        f'    }}'
        f'  }}'
        f'  function copy(){{'
        f'    var raw=g("gpjson-"+U)?g("gpjson-"+U).value:"";'
        f'    if(navigator.clipboard)navigator.clipboard.writeText(raw);'
        f'  }}'
        f'  window["_gp_"+U]={{run:run,copy:copy}};'
        f'  var ta=g("gpjson-"+U);'
        f'  if(ta)ta.addEventListener("input",function(){{clearTimeout(ta._t);ta._t=setTimeout(run,400);}});'
        f'  setTimeout(run,150);'
        f'}})();'
        f'</script>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# FANCY EMBED SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def render_embed(etype: str, src: str) -> str:
    """
    ::embed[type]{src}

    Types:
      youtube        - YouTube video (id or full URL, supports ?t= timestamp)
      youtube-nc     - YouTube via privacy-enhanced nocookie domain
      vimeo          - Vimeo video (id or URL)
      spotify        - Spotify track/album/playlist (URL)
      codepen        - CodePen pen (URL)
      github         - GitHub repo card (user/repo)
      twitter        - Twitter/X tweet embed (tweet URL)
      map            - Google Maps embed (place name or coordinates)
      pdf            - PDF viewer (URL)
      site           - Generic website iframe preview
      image          - Responsive image
      video          - HTML5 video (mp4/webm URL)
      audio          - HTML5 audio player
    """
    etype = etype.lower().strip()
    src   = src.strip()

    # ── YouTube ──────────────────────────────────────────────────────────────
    if etype in ('youtube', 'youtube-nc', 'yt'):
        # Extract video ID from various URL formats
        vid = src
        for pat in [r'v=([A-Za-z0-9_\-]{11})', r'youtu\.be/([A-Za-z0-9_\-]{11})',
                    r'embed/([A-Za-z0-9_\-]{11})']:
            m = re.search(pat, src)
            if m:
                vid = m.group(1)
                break
        # Extract timestamp
        ts = ''
        tm = re.search(r't=(\d+)', src)
        if tm:
            ts = f'&start={tm.group(1)}'
        domain = 'www.youtube-nocookie.com' if etype == 'youtube-nc' else 'www.youtube.com'
        url = f'https://{domain}/embed/{_esc(vid)}?rel=0&modestbranding=1{ts}'
        return (
            f'<div class="vml-embed vml-embed-video">'
            f'<div class="vml-embed-label">YouTube</div>'
            f'<iframe src="{url}" allowfullscreen loading="lazy" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">'
            f'</iframe></div>'
        )

    # ── Vimeo ─────────────────────────────────────────────────────────────────
    if etype == 'vimeo':
        vid = src
        m = re.search(r'vimeo\.com/(\d+)', src)
        if m:
            vid = m.group(1)
        elif re.match(r'^\d+$', src):
            vid = src
        url = f'https://player.vimeo.com/video/{_esc(vid)}?color=7c6dff&title=0&byline=0'
        return (
            f'<div class="vml-embed vml-embed-video">'
            f'<div class="vml-embed-label">Vimeo</div>'
            f'<iframe src="{url}" allowfullscreen loading="lazy"></iframe>'
            f'</div>'
        )

    # ── Spotify ──────────────────────────────────────────────────────────────
    if etype == 'spotify':
        # Convert open.spotify.com/track/ID → embed URL
        m = re.search(r'spotify\.com/(track|album|playlist|episode)/([A-Za-z0-9]+)', src)
        if m:
            kind, sid = m.group(1), m.group(2)
            url = f'https://open.spotify.com/embed/{kind}/{sid}?utm_source=generator&theme=0'
        else:
            url = _esc(src)
        return (
            f'<div class="vml-embed vml-embed-spotify">'
            f'<div class="vml-embed-label">Spotify</div>'
            f'<iframe src="{url}" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
            f'loading="lazy" style="height:152px"></iframe>'
            f'</div>'
        )

    # ── CodePen ──────────────────────────────────────────────────────────────
    if etype == 'codepen':
        # https://codepen.io/USER/pen/SLUG → embed
        m = re.search(r'codepen\.io/([^/]+)/pen/([^/?#]+)', src)
        if m:
            user, slug = m.group(1), m.group(2)
            url = f'https://codepen.io/{user}/embed/{slug}?default-tab=result&theme-id=dark'
        else:
            url = _esc(src)
        return (
            f'<div class="vml-embed vml-embed-codepen">'
            f'<div class="vml-embed-label">CodePen</div>'
            f'<iframe src="{url}" loading="lazy" allowfullscreen></iframe>'
            f'</div>'
        )

    # ── GitHub repo card ─────────────────────────────────────────────────────
    if etype == 'github':
        # src = "user/repo"
        parts = src.strip('/').split('/')
        user  = _esc(parts[0]) if parts else ''
        repo  = _esc(parts[1]) if len(parts) > 1 else ''
        uid   = _uid()
        return (
            f'<div class="vml-embed-github" id="gh-{uid}" '
            f'data-user="{user}" data-repo="{repo}">'
            f'<div class="vml-embed-label">GitHub</div>'
            f'<div class="vml-gh-card" id="ghc-{uid}">'
            f'<div class="vml-gh-loading">Loading repository info…</div>'
            f'</div>'
            f'</div>'
            f'<script>'
            f'(function(){{'
            f'  var U="{uid}",user="{user}",repo="{repo}";'
            f'  fetch("https://api.github.com/repos/"+user+"/"+repo)'
            f'  .then(function(r){{return r.json();}})'
            f'  .then(function(d){{'
            f'    var el=document.getElementById("ghc-"+U);'
            f'    if(!el)return;'
            f'    var lang=d.language||"";'
            f'    var stars=d.stargazers_count||0;'
            f'    var forks=d.forks_count||0;'
            f'    var desc=d.description||"No description";'
            f'    el.innerHTML='
            f'      "<div class=vml-gh-header>"'
            f'      +"<svg width=18 height=18 viewBox=\'0 0 24 24\' fill=\'currentColor\' style=\'color:#9ea3c0\'><path d=\'M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22\'/></svg>"'
            f'      +"<a class=vml-gh-name href=\'"+d.html_url+"\' target=_blank>"+user+"/"+repo+"</a>"'
            f'      +"</div>"'
            f'      +"<p class=vml-gh-desc>"+desc+"</p>"'
            f'      +"<div class=vml-gh-meta>"'
            f'      +(lang?"<span class=vml-gh-lang><span class=vml-gh-lang-dot></span>"+lang+"</span>":"")'
            f'      +"<span class=vml-gh-stat>★ "+stars+"</span>"'
            f'      +"<span class=vml-gh-stat>⑂ "+forks+"</span>"'
            f'      +"</div>";'
            f'  }})'
            f'  .catch(function(){{'
            f'    var el=document.getElementById("ghc-"+U);'
            f'    if(el)el.innerHTML="<div class=vml-gh-error>Could not load repository info.</div>";'
            f'  }});'
            f'}})();'
            f'</script>'
        )

    # ── Map (OpenStreetMap iframe, no API key needed) ─────────────────────────
    if etype == 'map':
        query = html.escape(src)
        # Check if it's lat,lon coordinates
        coord = re.match(r'^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$', src.strip())
        if coord:
            lat, lon = coord.group(1), coord.group(2)
            url = (f'https://www.openstreetmap.org/export/embed.html'
                   f'?bbox={float(lon)-0.01},{float(lat)-0.01},{float(lon)+0.01},{float(lat)+0.01}'
                   f'&layer=mapnik&marker={lat},{lon}')
        else:
            # Encode place name search
            enc = src.replace(' ', '+')
            url = f'https://www.openstreetmap.org/export/embed.html?query={html.escape(enc)}&layer=mapnik'
        return (
            f'<div class="vml-embed vml-embed-map">'
            f'<div class="vml-embed-label">📍 Map — {query}</div>'
            f'<iframe src="{url}" loading="lazy" '
            f'style="border:0" allowfullscreen></iframe>'
            f'<div class="vml-embed-link">'
            f'<a href="https://www.openstreetmap.org/search?query={html.escape(src)}" '
            f'target="_blank">Open in OpenStreetMap ↗</a>'
            f'</div>'
            f'</div>'
        )

    # ── PDF viewer ────────────────────────────────────────────────────────────
    if etype == 'pdf':
        url = _esc(src)
        return (
            f'<div class="vml-embed vml-embed-pdf">'
            f'<div class="vml-embed-label">📄 PDF</div>'
            f'<iframe src="{url}" loading="lazy" type="application/pdf"></iframe>'
            f'<div class="vml-embed-link"><a href="{url}" target="_blank">Open PDF ↗</a></div>'
            f'</div>'
        )

    # ── HTML5 Video ───────────────────────────────────────────────────────────
    if etype == 'video':
        url = _esc(src)
        ext = src.rsplit('.', 1)[-1].lower()
        mtype = {'mp4': 'video/mp4', 'webm': 'video/webm', 'ogg': 'video/ogg'}.get(ext, 'video/mp4')
        return (
            f'<div class="vml-embed vml-embed-video vml-embed-native">'
            f'<video controls loading="lazy" style="width:100%;border-radius:8px">'
            f'<source src="{url}" type="{mtype}">'
            f'Your browser does not support the video tag.'
            f'</video></div>'
        )

    # ── HTML5 Audio ───────────────────────────────────────────────────────────
    if etype == 'audio':
        url = _esc(src)
        return (
            f'<div class="vml-embed vml-embed-audio">'
            f'<div class="vml-embed-label">🎵 Audio</div>'
            f'<audio controls style="width:100%;margin-top:8px">'
            f'<source src="{url}">'
            f'</audio></div>'
        )

    # ── Generic site preview ──────────────────────────────────────────────────
    if etype == 'site':
        url = _esc(src)
        return (
            f'<div class="vml-embed vml-embed-site">'
            f'<div class="vml-embed-label">'
            f'🌐 <a href="{url}" target="_blank">{url}</a>'
            f'</div>'
            f'<iframe src="{url}" loading="lazy" sandbox="allow-scripts allow-same-origin"></iframe>'
            f'<div class="vml-embed-link"><a href="{url}" target="_blank">Open site ↗</a></div>'
            f'</div>'
        )

    # ── Image ────────────────────────────────────────────────────────────────
    if etype == 'image':
        return f'<img class="vml-embed-img" src="{_esc(src)}" alt="embedded image" loading="lazy">'

    # ── Unknown fallback ─────────────────────────────────────────────────────
    return (
        f'<div class="vml-embed-generic">'
        f'<a href="{_esc(src)}" target="_blank" rel="noopener">{_esc(src)}</a>'
        f'</div>'
    )

    # ── Unknown fallback ─────────────────────────────────────────────────────
    return (
        f'<div class="vml-embed-generic">'
        f'<a href="{_esc(src)}" target="_blank" rel="noopener">{_esc(src)}</a>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# Syntax: ::footer[copyright text|accent_colour]{col1||col2||col3}
# The body is split by || into columns.  A single-segment body gets centered.
# ══════════════════════════════════════════════════════════════════════════════

def render_footer(arg: str, content: str) -> str:
    """
    ::footer[copyright|accent]{col1 content||col2 content||col3 content}

    Renders a full-width site footer with up to 3 columns and a copyright bar.
    Any column can contain Markdown-rendered content, badges, icons, buttons, links.

    Arguments
    ---------
    copyright : short text shown in the bottom bar, e.g. '© 2025 Divyanshu Sinha'
    accent    : optional hex colour for the top border gradient (default: #7c6dff)

    Single-segment body → full-width centered block (good for minimal footers).
    Multi-segment body  → auto-fitted columns (flex, wrapping).

    Syntax examples
    ---------------
    Minimal:
      ::footer[© 2025 Divyanshu Sinha]{Built with **VoxMark**}

    Full 3-column:
      ::footer[© 2025 Divyanshu Sinha|#38d9a9]{
        **VoxMark**
        A custom Markdown + VML engine.
        ||
        **Links**
        ::icon[github|1em|#7c6dff]{} [GitHub](https://github.com/DivyanshuSinha136)
        ::icon[mail|1em|#38d9a9]{} [Email](mailto:divyanshu.sinha631@gmail.com)
        ||
        **Built with**
        ::badge[Python|#3b82f6] ::badge[Flask|#22c55e] ::badge[NASM|#f59e0b]
      }
    """
    parts     = [p.strip() for p in arg.split('|')]
    copyright = parts[0].strip() if parts else ''
    accent    = parts[1].strip() if len(parts) > 1 and parts[1].strip() else '#7c6dff'

    segments  = [s.strip() for s in content.split('||')]
    uid       = _uid()

    # Run a mini VML + Markdown pass on each column so widgets inside footer
    # (badges, icons, buttons, etc.) render correctly
    def _render_col_text(text: str) -> str:
        t = VMLTransformer()
        rendered = t.transform(text)
        # Simple inline-Markdown for **bold**, *italic*, `code`, [links](url)
        import re as _re
        rendered = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', rendered)
        rendered = _re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         rendered)
        rendered = _re.sub(r'`(.+?)`',        r'<code>\1</code>',     rendered)
        rendered = _re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                           r'<a href="\2">\1</a>', rendered)
        return rendered

    if len(segments) == 1:
        inner_html = (
            f'<div class="vml-footer-center">{_render_col_text(segments[0])}</div>'
        )
    else:
        cols = ''.join(
            f'<div class="vml-footer-col">{_render_col_text(seg)}</div>'
            for seg in segments if seg
        )
        inner_html = f'<div class="vml-footer-cols">{cols}</div>'

    copyright_bar = (
        f'<div class="vml-footer-bar">'
        f'<span class="vml-footer-copy">{_esc(copyright)}</span>'
        f'<span class="vml-footer-made">Made with '
        f'<span class="vml-footer-heart">♥</span>'
        f' using VoxMark</span>'
        f'</div>'
    ) if copyright else ''

    return (
        f'<footer class="vml-footer" id="vml-footer-{uid}" '
        f'style="--footer-accent:{_esc(accent)}">'
        f'<div class="vml-footer-inner">'
        f'{inner_html}'
        f'</div>'
        f'{copyright_bar}'
        f'</footer>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# Syntax: :::sidebar[Title|side|width]{nav_item1||nav_item2||...}
# side  = left (default) | right
# width = CSS width (default: 260px)
# Each nav segment: LinkText::url  OR just content HTML/Markdown.
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar(arg: str, content: str) -> str:
    """
    :::sidebar[Title|side|width]{
      Home::/#home
      ||About::#about
      ||Projects::#projects
      ||Contact::#contact
    }

    Renders a collapsible slide-in sidebar with a floating toggle button.
    Clicking outside or pressing Escape closes it.

    Arguments
    ---------
    Title : sidebar heading / site name (shown at top of sidebar)
    side  : 'left' (default) or 'right' — which edge the sidebar slides from
    width : CSS width string, default '260px'

    Body segments (|| separated)
    ----------------------------
    Each segment is a nav item, written as:
      Label Text::href      → renders as a nav <a> link
      Label Text            → renders as a nav section heading (no link)
      ---                   → renders as a visual divider

    Any segment not matching Label::href is rendered as raw HTML/Markdown,
    so you can embed badges, icons, or any VML widget inside the sidebar.

    Syntax example
    --------------
    :::sidebar[MyPortfolio|left|280px]{
      Home::#home
      ||About::#about
      ||Projects::#projects
      ||---
      ||::badge[v2.0|#7c6dff]
      ||Contact::#contact
    }
    """
    parts = [p.strip() for p in arg.split('|')]
    title = parts[0].strip() if parts else 'Menu'
    side  = 'right' if len(parts) > 1 and parts[1].strip().lower() == 'right' else 'left'
    width = parts[2].strip() if len(parts) > 2 and parts[2].strip() else '260px'
    uid   = _uid()

    nav_items_html = ''
    for seg in content.split('||'):
        seg = seg.strip()
        if not seg:
            continue

        # Check if this segment is (or starts with) a divider line
        # Support "---" alone OR "---\nmore content" (divider then widget)
        lines = seg.splitlines()
        first_line = lines[0].strip()
        rest = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''

        if first_line == '---':
            nav_items_html += '<hr class="vml-sidebar-divider">'
            if rest:
                # There's more content after the divider in the same segment
                seg = rest
            else:
                continue

        if seg == '---':
            nav_items_html += '<hr class="vml-sidebar-divider">'
            continue
        if '::' in seg and not seg.startswith('::'):
            # Label::href pattern
            label, _, href = seg.partition('::')
            label = label.strip()
            href  = href.strip()
            nav_items_html += (
                f'<a class="vml-sidebar-link" href="{_esc(href)}" '
                f'onclick="vmlSidebarClose(\'{uid}\')">'
                f'{_esc(label)}'
                f'</a>'
            )
        elif '::' in seg or '<' in seg:
            # Raw HTML/VML widget content
            nav_items_html += f'<div class="vml-sidebar-widget">{seg}</div>'
        else:
            # Plain text → section heading
            nav_items_html += f'<div class="vml-sidebar-heading">{_esc(seg)}</div>'

    transform_open  = f'translateX({"-" if side == "left" else ""}100%)'
    transform_close = 'translateX(0)'
    edge_css        = f'{side}:0'
    btn_edge        = 'left:16px' if side == 'left' else 'right:16px'

    return (
        f'<!-- VML Sidebar: {title} -->'
        f'<div class="vml-sidebar-overlay" id="vml-sbo-{uid}" '
        f'onclick="vmlSidebarClose(\'{uid}\')" style="display:none"></div>'
        f'<nav class="vml-sidebar" id="vml-sb-{uid}" '
        f'style="width:{_esc(width)};{edge_css};'
        f'transform:{transform_open}">'
        f'<div class="vml-sidebar-header">'
        f'<span class="vml-sidebar-title">{_esc(title)}</span>'
        f'<button class="vml-sidebar-close" '
        f'onclick="vmlSidebarClose(\'{uid}\')" '
        f'aria-label="Close sidebar">✕</button>'
        f'</div>'
        f'<div class="vml-sidebar-nav">{nav_items_html}</div>'
        f'</nav>'
        f'<button class="vml-sidebar-toggle" id="vml-sbt-{uid}" '
        f'style="{btn_edge}" '
        f'onclick="vmlSidebarOpen(\'{uid}\')" '
        f'aria-label="Open {_esc(title)} sidebar">'
        f'<span class="vml-sidebar-toggle-icon">☰</span>'
        f'</button>'
        f'<script>'
        f'(function(){{'
        f'  function open_{uid}(){{'
        f'    var sb  = document.getElementById("vml-sb-{uid}");'
        f'    var ov  = document.getElementById("vml-sbo-{uid}");'
        f'    var btn = document.getElementById("vml-sbt-{uid}");'
        f'    if(!sb)return;'
        f'    sb.style.transform="{transform_close}";'
        f'    sb.setAttribute("aria-hidden","false");'
        f'    ov.style.display="block";'
        f'    btn.style.display="none";'
        f'  }}'
        f'  function close_{uid}(){{'
        f'    var sb  = document.getElementById("vml-sb-{uid}");'
        f'    var ov  = document.getElementById("vml-sbo-{uid}");'
        f'    var btn = document.getElementById("vml-sbt-{uid}");'
        f'    if(!sb)return;'
        f'    sb.style.transform="{transform_open}";'
        f'    sb.setAttribute("aria-hidden","true");'
        f'    ov.style.display="none";'
        f'    btn.style.display="flex";'
        f'  }}'
        f'  window.vmlSidebarOpen  = window.vmlSidebarOpen  || {{}};'
        f'  window.vmlSidebarClose = window.vmlSidebarClose || {{}};'
        f'  window.vmlSidebarOpen["{uid}"]  = open_{uid};'
        f'  window.vmlSidebarClose["{uid}"] = close_{uid};'
        f'  window.vmlSidebarOpen  = function(id){{  (window.vmlSidebarOpen[id]  ||function(){{}})(); }};'
        f'  window.vmlSidebarClose = function(id){{  (window.vmlSidebarClose[id] ||function(){{}})(); }};'
        f'  document.addEventListener("keydown",function(e){{'
        f'    if(e.key==="Escape")close_{uid}();'
        f'  }});'
        f'}})();'
        f'</script>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# Syntax: ::router[default_page]{page_id:Title::content||page_id2:Title2::content}
# OR at build time: ::router[home]{home:Home::./home.vml||about:About::./about.vml}
# Each segment: page_id:Page Title::body_content
# Hash-based client-side routing (#page_id in URL).
# ══════════════════════════════════════════════════════════════════════════════

def render_router(arg: str, body: str, resolve_file=None) -> str:
    """
    ::router[default_page_id]{
      home:Home::Home page content here...
      ||about:About::About page content here...
      ||projects:Projects::Projects content here...
    }

    Renders a hash-based single-page router.  Each || segment defines one page:
      page_id:Page Title::page body content

    Navigation links are auto-generated and can also be embedded anywhere
    as plain Markdown links: [Go to About](#about)

    Arguments
    ---------
    default_page_id : the page_id shown on first load (default: first page)

    Body segment format
    -------------------
    Each segment must be:   page_id:Display Title::body content
    - page_id    : URL-safe identifier (used as #hash)
    - Page Title : shown in the nav and as the browser title suffix
    - body       : any VML/Markdown content for that page

    File inclusion (build-time, handled by compiler)
    ------------------------------------------------
    If body content starts with 'file://', the router widget signals the
    compiler to read that path.  At language level the raw content is used.

    Syntax example
    --------------
    ::router[home]{
      home:Home::# Welcome\\nThis is the home page.
      ||about:About::# About\\nLearn more about me.
      ||work:Work::# Projects\\n::card[VoxMark]{A compiler.}
    }
    """
    uid          = _uid()
    default_page = arg.strip() or ''
    pages: list[tuple[str, str, str]] = []   # (id, title, content)

    for seg in body.split('||'):
        seg = seg.strip()
        if not seg:
            continue
        # Expect: page_id:Title::content
        if '::' not in seg:
            continue
        head, _, content = seg.partition('::')
        head = head.strip()
        content = content.strip()
        if ':' in head:
            pid, _, ptitle = head.partition(':')
            pid    = pid.strip()
            ptitle = ptitle.strip()
        else:
            pid    = re.sub(r'[^\w\-]', '', head.lower())
            ptitle = head

        if not pid:
            continue

        # Build-time file resolution
        if resolve_file and content.startswith('file://'):
            fpath = content[7:].strip()
            try:
                content = resolve_file(fpath)
            except Exception:
                content = f'<p class="vml-error">Could not include: {_esc(fpath)}</p>'

        pages.append((pid, ptitle, content))

    if not pages:
        return '<div class="vml-router-empty">Router: no pages defined.</div>'

    if not default_page:
        default_page = pages[0][0]

    # Build nav
    nav_html = ''.join(
        f'<a class="vml-router-nav-link" '
        f'href="#{_esc(pid)}" '
        f'data-page="{_esc(pid)}" '
        f'onclick="vmlRoute(\'{uid}\',\'{_esc(pid)}\');return false;">'
        f'{_esc(ptitle)}</a>'
        for pid, ptitle, _ in pages
    )

    # Build page sections
    pages_html = ''.join(
        f'<section class="vml-router-page" '
        f'id="vml-rp-{uid}-{_esc(pid)}" '
        f'data-page="{_esc(pid)}" '
        f'style="display:none">'
        f'{content}'
        f'</section>'
        for pid, ptitle, content in pages
    )

    page_ids_js = json.dumps([pid for pid, _, _ in pages])
    titles_js   = json.dumps({pid: ptitle for pid, ptitle, _ in pages})

    return (
        f'<div class="vml-router" id="vml-router-{uid}" '
        f'data-default="{_esc(default_page)}">'
        f'<nav class="vml-router-nav" role="navigation" aria-label="Page navigation">'
        f'{nav_html}'
        f'</nav>'
        f'<div class="vml-router-body">'
        f'{pages_html}'
        f'</div>'
        f'</div>'
        f'<script>'
        f'(function(){{'
        f'  var UID   = "{uid}";'
        f'  var PAGES = {page_ids_js};'
        f'  var TITLES= {titles_js};'
        f'  var DEF   = "{_esc(default_page)}";'
        f'  function showPage(pid){{'
        f'    if(PAGES.indexOf(pid)<0)pid=DEF;'
        f'    PAGES.forEach(function(p){{'
        f'      var sec = document.getElementById("vml-rp-"+UID+"-"+p);'
        f'      var lnk = document.querySelector('
        f'        "#vml-router-"+UID+" .vml-router-nav-link[data-page=\'"+p+"\']");'
        f'      if(sec)sec.style.display=(p===pid)?"block":"none";'
        f'      if(lnk)lnk.classList.toggle("active",p===pid);'
        f'    }});'
        f'    if(TITLES[pid])document.title=TITLES[pid]+" — "+document.title.split(" — ").pop();'
        f'    if(history.replaceState)history.replaceState(null,"","#"+pid);'
        f'  }}'
        f'  window.vmlRoute=function(uid,pid){{if(uid===UID)showPage(pid);}};'
        f'  window.addEventListener("hashchange",function(){{'
        f'    var h=location.hash.replace("#","");'
        f'    if(PAGES.indexOf(h)>=0)showPage(h);'
        f'  }});'
        f'  var initial=location.hash.replace("#","");'
        f'  showPage(PAGES.indexOf(initial)>=0?initial:DEF);'
        f'}})();'
        f'</script>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# INCLUDE  (build-time — reads another .vml file and inlines its rendered HTML)
# Syntax: ::include[./path/to/file.vml]
# The actual file reading is done in compiler.py / renderer.py before this
# render function is called; by the time it reaches here, `content` is the
# already-rendered HTML of the included file.
# ══════════════════════════════════════════════════════════════════════════════

def render_include(path: str, content: str) -> str:
    """
    ::include[./path/to/file.vml]

    Build-time include: reads the target .vml file, renders it through the
    full VML pipeline, and inlines the result here.

    - Paths are relative to the source file being compiled.
    - Supports .vml and .md extensions.
    - Circular includes are detected and skipped.
    - The included file is wrapped in a <div class="vml-include"> so CSS
      scoping (if needed) can target included content separately.
    - At language.py level this function just wraps the already-rendered HTML
      passed in from the compiler; the file I/O happens in compiler.py.

    Syntax example
    --------------
    ::include[./sections/hero.vml]
    ::include[./partials/footer.vml]
    ::include[../shared/header.vml]
    """
    safe_path = html.escape(path.strip())
    if not content.strip():
        return (
            f'<div class="vml-include vml-include-empty" '
            f'data-src="{safe_path}">'
            f'<!-- include: {safe_path} (empty or missing) -->'
            f'</div>'
        )
    return (
        f'<div class="vml-include" data-src="{safe_path}">'
        f'{content}'
        f'</div>'
    )


# ── main VML transformer ──────────────────────────────────────────────────────

class VMLTransformer:
    """
    Transforms VML syntax into HTML.

    New in this version:
      - ::input[type|placeholder|id]{label}   — styled form input
      - ::checkbox[id|value|checked]{label}   — styled checkbox
      - ::select[id|default|label]{opt1|opt2} — styled dropdown
      - ::if[cond]{content}                   — show when truthy
      - ::else[cond]{content}                 — show when falsy
      - ::ifelse[cond]{then||else}            — inline branch
      - ::class_def[Name]{k:v||k2:v2}        — define a named namespace
      - @ClassName.property                   — access a class property
    """

    # Patterns ordered by specificity
    TRIPLE_PATTERN = re.compile(
        r':::(?P<cmd>\w+)(?:\[(?P<arg>[^\]]*)\])?\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}',
        re.DOTALL
    )
    DOUBLE_PATTERN = re.compile(
        r'::(?P<cmd>\w+)(?:\[(?P<arg>[^\]]*)\])?\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}',
        re.DOTALL
    )
    # Bodyless: ::cmd[arg] with no {} body
    BODYLESS_PATTERN = re.compile(
        r'::(?P<cmd>divider|spacer|badge|progress)(?:\[(?P<arg>[^\]]*)\])?(?!\{)',
    )
    # Simple @name var refs (single-word, no dot)
    VAR_USE = re.compile(r'@([A-Za-z]\w*)(?!\.\w)')
    # @ClassName.property refs
    CLASS_REF_PAT = re.compile(r'@([A-Za-z]\w*)\.(\w+)')

    # HTML regions that must not be re-processed for VML syntax (already rendered)
    _HTML_PROTECT_PAT = re.compile(
        r'(<(?:pre|code|style)[^>]*>)(.*?)(</(?:pre|code|style)>)',
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(self):
        self._vars:    dict[str, str]             = {}
        self._classes: dict[str, dict[str, str]]  = {}

    # ── triple-colon dispatch ─────────────────────────────────────────────────

    def _handle_triple(self, m: re.Match) -> str:
        cmd  = m.group('cmd').lower()
        arg  = m.group('arg') or ''
        body = m.group('body') or ''
        return self.dispatch_triple(cmd, arg, body)

    def dispatch_triple(self, cmd: str, arg: str, body: str) -> str:
        cmd = cmd.lower()
        if cmd == 'fold':
            return render_fold(arg, self._process_inner(body))
        if cmd == 'demo':
            return render_demo(body)
        if cmd == 'btngroup':
            return render_button_group(self._process_inner(body))
        if cmd == 'svg':
            return render_svg(body)
        if cmd == 'css':
            return render_css_block(body, _uid())
        if cmd == 'cssplay':
            return render_cssplay(body)
        if cmd == 'div':
            return render_div(arg, self._process_inner(body))
        if cmd == 'box':
            return render_box(arg, self._process_inner(body))
        if cmd == 'hero':
            return render_hero(arg, self._process_inner(body))
        if cmd == 'grid':
            return render_grid(arg, self._process_inner(body))
        if cmd == 'flex':
            return render_flex(arg, self._process_inner(body))
        if cmd == 'section':
            return render_section(arg, self._process_inner(body))
        if cmd == 'graphplay':
            return render_graphplay(body)
        if cmd == 'sidebar':
            return render_sidebar(arg, self._process_inner(body))
        return f':::{cmd}[{arg}]{{{body}}}'   # unknown — leave as-is

    # ── double-colon dispatch ─────────────────────────────────────────────────

    def _handle_double(self, m: re.Match) -> str:
        cmd  = m.group('cmd').lower()
        arg  = m.group('arg') or ''
        body = m.group('body') or ''
        return self.dispatch_double(cmd, arg, body)

    def dispatch_double(self, cmd: str, arg: str, body: str) -> str:
        cmd = cmd.lower()

        # ── Commands that use raw body directly (no _process_inner needed) ────
        # These handle their own segment splitting / use body as literal data.
        RAW_BODY_CMDS = {
            'var', 'class_def',
            'input', 'checkbox', 'select',
            'if', 'else', 'ifelse',
            'kbd', 'cssvar',
            'footer', 'router', 'include',
            'math', 'embed', 'chart',
            'css', 'cssplay', 'graphplay', 'graph', 'svg', 'demo',
        }
        if cmd not in RAW_BODY_CMDS:
            inner = self._process_inner(body)
        else:
            inner = body  # will be overridden per-command or unused

        # ── Variables & classes ───────────────────────────────────────────────
        if cmd == 'var':
            self._vars[arg] = body
            return ''

        if cmd == 'class_def':
            result = define_class(arg, body)
            # Store class in this transformer instance for @Name.prop resolution
            safe_name = re.sub(r'[^\w]', '', arg).strip()
            if safe_name in _VML_CLASSES:
                self._classes[safe_name] = _VML_CLASSES[safe_name]
            return result

        # ── Inputs & forms ────────────────────────────────────────────────────
        if cmd == 'input':
            return render_input(arg, body)         # body IS the label, no Markdown

        if cmd == 'checkbox':
            return render_checkbox(arg, body)      # body IS the label

        if cmd == 'select':
            return render_select(arg, body)        # body is pipe-sep options list

        # ── Control flow ──────────────────────────────────────────────────────
        if cmd == 'if':
            return render_if(arg, inner)

        if cmd == 'else':
            return render_else(arg, inner)

        if cmd == 'ifelse':
            return render_ifelse(arg, body)        # handles || split internally

        # ── Content widgets ───────────────────────────────────────────────────
        if cmd == 'card':
            return render_card(arg, inner)
        if cmd == 'tab':
            return render_tab(arg, inner)
        if cmd == 'alert':
            return render_alert(arg, inner)
        if cmd == 'badge':
            parts = arg.split('|')
            color = parts[1].strip() if len(parts) > 1 else '#6c63ff'
            return render_badge(parts[0].strip(), color)
        if cmd == 'progress':
            parts  = arg.split('|')
            vals   = parts[0].split('/')
            value  = vals[0].strip() if vals else '0'
            maxval = vals[1].strip() if len(vals) > 1 else '100'
            label  = parts[1].strip() if len(parts) > 1 else ''
            return render_progress(value, maxval, label)
        if cmd == 'columns':
            return render_columns(arg, inner)
        if cmd == 'callout':
            return render_callout(arg or '💡', inner)
        if cmd == 'kbd':
            return render_kbd(body)
        if cmd == 'tooltip':
            return render_tooltip(arg, inner)
        if cmd == 'timeline':
            return render_timeline(body)
        if cmd == 'math':
            return render_math(body)
        if cmd == 'color':
            return render_color(arg, inner)
        if cmd == 'glow':
            return render_glow(arg, inner)
        if cmd == 'embed':
            return render_embed(arg, body.strip())
        if cmd == 'chart':
            return self._render_chart(arg, body)
        if cmd == 'graph':
            return render_graph(arg, body)
        if cmd == 'center':
            return render_center(inner)
        if cmd == 'right':
            return render_right(inner)
        if cmd == 'divider':
            return render_divider(arg)
        if cmd == 'spacer':
            return render_spacer(arg)
        if cmd == 'button':
            parts  = arg.split('|')
            style  = parts[0].strip() if parts else 'primary'
            action = parts[1].strip() if len(parts) > 1 else '#'
            return render_button(inner, style, action)
        if cmd == 'hl':
            return render_highlight(arg, inner)
        if cmd == 'b':
            return render_bold_styled(arg, inner)
        if cmd == 'icon':
            parts = arg.split('|')
            name  = parts[0].strip() if parts else 'box'
            size  = parts[1].strip() if len(parts) > 1 else '1em'
            color = parts[2].strip() if len(parts) > 2 else ''
            return render_icon(name, size, color)
        if cmd == 'iconcard':
            parts     = arg.split('|')
            icon_name = parts[0].strip() if parts else 'box'
            title     = parts[1].strip() if len(parts) > 1 else ''
            return render_svg_icon_card(icon_name, title, inner)
        if cmd == 'style':
            return render_style_wrapper(arg, inner)
        if cmd == 'class':
            return render_css_class(arg, inner)
        if cmd == 'cssvar':
            return render_css_var(arg, body.strip())
        # ── Layout / navigation ───────────────────────────────────────────────
        if cmd == 'footer':
            return render_footer(arg, body)          # render_footer splits || itself
        if cmd == 'router':
            return render_router(arg, body)          # raw body — :: is router's field sep
        if cmd == 'include':
            return render_include(arg, body)
        return f'::{cmd}[{arg}]{{{body}}}'  # unknown — leave as-is

    # ── bodyless dispatch ─────────────────────────────────────────────────────

    def _handle_bodyless(self, m: re.Match) -> str:
        cmd = m.group('cmd').lower()
        arg = m.group('arg') or ''
        return self.dispatch_bodyless(cmd, arg)

    def dispatch_bodyless(self, cmd: str, arg: str) -> str:
        cmd = cmd.lower()
        if cmd == 'divider':
            return render_divider(arg)
        if cmd == 'spacer':
            return render_spacer(arg)
        if cmd == 'badge':
            parts = arg.split('|')
            text  = parts[0].strip() if parts else ''
            color = parts[1].strip() if len(parts) > 1 else '#6c63ff'
            return render_badge(text, color)
        if cmd == 'progress':
            parts  = arg.split('|')
            vals   = parts[0].split('/') if parts else ['0', '100']
            value  = vals[0].strip() if vals else '0'
            maxval = vals[1].strip() if len(vals) > 1 else '100'
            label  = parts[1].strip() if len(parts) > 1 else ''
            return render_progress(value, maxval, label)
        return f'::{cmd}[{arg}]'  # unknown — leave as-is

    # ── helpers ───────────────────────────────────────────────────────────────

    def _render_chart(self, chart_type: str, data_raw: str) -> str:
        uid = _uid()
        try:
            data = json.loads(data_raw.strip())
        except Exception:
            return '<div class="vml-error">Chart: invalid JSON data</div>'
        payload = json.dumps({'type': chart_type, 'data': data})
        return (
            f'<div class="vml-chart-wrap">'
            f'<canvas id="vc-{uid}" class="vml-chart" '
            f'data-chart=\'{payload}\'></canvas>'
            f'</div>'
        )

    def _process_inner(self, text: str) -> str:
        return self.transform(text)

    def _apply_var_uses(self, text: str) -> str:
        # 1. Resolve @ClassName.property first (more specific)
        merged_classes = {**_VML_CLASSES, **self._classes}
        text = resolve_class_refs(text, merged_classes)
        # 2. Then resolve simple @name vars
        def _replace_var(m: re.Match) -> str:
            return self._vars.get(m.group(1), m.group(0))
        return self.VAR_USE.sub(_replace_var, text)

    def _safe_sub(self, pattern: re.Pattern, handler):
        """Wrap a regex handler so one bad widget can't crash the whole render."""
        def _guarded(m: re.Match) -> str:
            try:
                return handler(m)
            except Exception as exc:
                import logging
                logging.getLogger('voxmark.language').warning(
                    'VML widget render failed (%s): %s', m.group(0)[:60], exc
                )
                return m.group(0)
        return _guarded

    def transform(self, text: str) -> str:
        """
        Apply all VML patterns to text then resolve variable/class references.

        Protected regions: <pre>, <code>, and <style> tag contents are stashed
        before pattern matching and restored afterward — they are already-rendered
        HTML where any '::widget{...}' text is literal display content, not a
        command to execute (e.g. Pygments code blocks, inline code spans, CSS).
        """
        # ── Stash <pre>/<code>/<style> contents ──────────────────────────────
        html_stash: list[str] = []

        def _protect(m: re.Match) -> str:
            slot = len(html_stash)
            html_stash.append(m.group(0))
            return f'\x00HTMLSTASH{slot}\x00'

        text = self._HTML_PROTECT_PAT.sub(_protect, text)

        # ── Apply VML patterns only to the unprotected regions ───────────────
        text = self.BODYLESS_PATTERN.sub(self._safe_sub(self.BODYLESS_PATTERN, self._handle_bodyless), text)
        text = self.TRIPLE_PATTERN.sub(self._safe_sub(self.TRIPLE_PATTERN, self._handle_triple), text)
        text = self.DOUBLE_PATTERN.sub(self._safe_sub(self.DOUBLE_PATTERN, self._handle_double), text)
        text = self._apply_var_uses(text)

        # ── Restore stashed HTML ─────────────────────────────────────────────
        for i, saved in enumerate(html_stash):
            text = text.replace(f'\x00HTMLSTASH{i}\x00', saved, 1)

        return text


# ── public API ────────────────────────────────────────────────────────────────

_transformer = VMLTransformer()

def transform_vml(text: str) -> str:
    """Transform VML syntax in text, return HTML."""
    _transformer._vars = {}  # reset vars per render
    return _transformer.transform(text)