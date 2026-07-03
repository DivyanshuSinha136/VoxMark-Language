"""
VoxMark built-in example documents.
Author: Divyanshu Sinha
"""

WELCOME_DOC = r"""
# Welcome to **VoxMark** ✦

::alert[info]{This is **VoxMark** — a Markdown editor supercharged with the **VML** (VoxMark Language) extension system. Edit on the left, see results instantly on the right.}

---

## What is VML?

VML adds **interactive widgets** directly inside your Markdown using a clean `::widget[args]{content}` syntax. No JavaScript required in your documents — everything renders automatically.

::columns[1:1]{
### Markdown Support
Full CommonMark + GFM support. Tables, task lists, fenced code, images — all rendered with beautiful typography.
||
### VML Extensions
26+ widget types: cards, tabs, alerts, timelines, progress bars, charts, live demos, and more.
}

---

## Quick Widget Tour

### Cards

::card[🚀 Getting Started]{Write your Markdown + VML in the **editor panel** on the left. The preview updates **instantly** as you type, powered by a debounced render pipeline.}

::card[⚡ Keyboard Shortcuts]{Press ::kbd{Ctrl+Enter} to force a render, ::kbd{Ctrl+S} to export HTML, and ::kbd{Ctrl+/} to toggle the editor/preview split.}

### Alerts

::alert[success]{Your document renders in real-time — no build step needed.}
::alert[warn]{VML widgets are sanitized server-side before display.}
::alert[error]{This is what an error alert looks like.}

### Tabs

::tab[Python|JavaScript|Rust]{
```python
def hello(name: str) -> str:
    return f"Hello, {name}!"

print(hello("VoxMark"))
```
||
```javascript
const hello = name => `Hello, ${name}!`;
console.log(hello("VoxMark"));
```
||
```rust
fn hello(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn main() {
    println!("{}", hello("VoxMark"));
}
```
}

### Progress Bars

::progress[72/100|Project Completion]
::progress[3/5|Milestones]
::progress[1/1|Tests Passing]

### Timeline

::timeline{Project Kickoff::Divyanshu started VoxMark as a production-grade document platform.||VML v1 Spec::Designed the VoxMark Language (VML) with 26+ widget types.||First Release::Shipped the integrated server with built-in firewall and live preview.||You Are Here::Explore, edit, and create your own VML documents!}

### Callout

::callout[💡]{**Pro Tip:** Use `::var[name]{value}` to define reusable variables, then reference them anywhere with `@name`.}

### Badges

Status: ::badge[stable|#22c55e] Version: ::badge[1.0.0|#6c63ff] License: ::badge[MIT|#f59e0b]

---

## Code with Syntax Highlighting

```python
# VoxMark render pipeline
from voxmark.renderer import render

source = (
    "# Hello World\n"
    "::alert[success]{It works!}\n"
)

html_output = render(source)
print(html_output)
```

---

## Tables Work Too

| Widget     | Syntax                    | Description             |
|------------|---------------------------|-------------------------|
| Card       | `::card[title]{body}`     | Content card            |
| Alert      | `::alert[type]{msg}`      | Status alert            |
| Progress   | `::progress[v/max\|lbl]`  | Progress bar            |
| Tabs       | `::tab[A\|B]{c1\|\|c2}`   | Tabbed content          |
| Timeline   | `::timeline{a\|\|b}`      | Vertical timeline       |
| Glow       | `::glow[#f0f]{text}`      | Glowing text            |
| Fold       | `:::fold[title]{body}`    | Collapsible section     |

---

## Collapsible Sections

:::fold[Advanced VML Reference]{
### Variable System

Define once:
```
::var[author]{Divyanshu Sinha}
```

Use anywhere: The author of this document is @author.

### Conditional Blocks (Client-Side)

```
::if[darkMode]{This shows in dark mode only}
```

### Glow Text

::glow[#6c63ff]{VoxMark glows in the dark.}

### Colored Text

::color[#f59e0b]{Amber} ::color[#22c55e]{Green} ::color[#ef4444]{Red}
}

---

## ::b[gradient]{Buttons}

Six styles, full hover animations:

:::btngroup{::button[primary|#]{Get Started}||::button[secondary|#]{Learn More}||::button[ghost|#]{Docs}||::button[outline|#]{GitHub}||::button[danger|#]{Delete}||::button[success|#]{Confirm}}

Buttons work as links too: ::button[primary|https://github.com/DivyanshuSinha136]{::icon[github|1em|#fff]{} GitHub}

---

## ::b[neon]{Highlighted & Styled Text}

Normal highlights: ::hl[yellow]{important} ::hl[green]{success} ::hl[pink]{warning} ::hl[blue]{info} ::hl[orange]{note} ::hl[purple]{vml}

Styled bold variants:

- ::b[gradient]{Gradient} — multicolor gradient fill
- ::b[outline]{Outline} — transparent with stroke
- ::b[shadow]{Shadow} — layered drop shadow
- ::b[neon]{Neon} — glowing neon effect
- ::b[stamp]{STAMP} — uppercase bordered stamp
- ::b[underline]{Underline} — accent underline
- ::b[mono]{mono} — monospace code-style bold

---

## ::b[outline]{Icons} ::icon[star|1em|#f59e0b]{}

30+ built-in SVG icons, inline and crisp at any size:

::columns[1:1]{
**Navigation & UI**

::icon[home|1.2em|#7c6dff]{} Home  ·  ::icon[search|1.2em|#7c6dff]{} Search  ·  ::icon[settings|1.2em|#7c6dff]{} Settings  ·  ::icon[bell|1.2em|#f59e0b]{} Bell  ·  ::icon[user|1.2em|#38d9a9]{} User  ·  ::icon[mail|1.2em|#3b82f6]{} Mail  ·  ::icon[eye|1.2em|#9ca3af]{} Eye
||
**Actions & Status**

::icon[check-circle|1.2em|#22c55e]{} Done  ·  ::icon[x-circle|1.2em|#ef4444]{} Error  ·  ::icon[info|1.2em|#3b82f6]{} Info  ·  ::icon[warn|1.2em|#f59e0b]{} Warn  ·  ::icon[download|1.2em|#7c6dff]{} DL  ·  ::icon[upload|1.2em|#38d9a9]{} UL  ·  ::icon[trash|1.2em|#ef4444]{} Del
}

### Icon Cards

::columns[1:1:1]{
::iconcard[rocket|Fast Render]{Sub-millisecond VML transforms with Python's compiled regex engine.}
||
::iconcard[lock|Secure]{Integrated firewall with XSS scanning and rate limiting built-in.}
||
::iconcard[layers|Extensible]{30+ widget types — cards, tabs, charts, icons, buttons and more.}
}

---

## ::b[stamp]{INLINE SVG}

Fully sanitized raw SVG blocks — render diagrams, logos, or art directly:

:::svg{<svg viewBox="0 0 320 80" xmlns="http://www.w3.org/2000/svg" width="320" height="80"><defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#7c6dff"/><stop offset="50%" style="stop-color:#38d9a9"/><stop offset="100%" style="stop-color:#f59e0b"/></linearGradient></defs><rect width="320" height="80" rx="14" fill="#13162a" stroke="#252a44" stroke-width="1.5"/><text x="24" y="30" font-family="system-ui,sans-serif" font-size="11" fill="#5c627a" letter-spacing="3" text-transform="uppercase">VOXMARK ENGINE</text><text x="24" y="58" font-family="system-ui,sans-serif" font-size="22" font-weight="700" fill="url(#g1)">Markdown + VML</text><circle cx="290" cy="40" r="20" fill="#7c6dff22" stroke="#7c6dff55"/><text x="290" y="46" font-size="16" text-anchor="middle" fill="#7c6dff">V</text></svg>}

---

> "The best documentation system is one that gets out of your way."
> — Divyanshu Sinha

---

## ::b[gradient]{CSS Support} ::icon[layers|1em|#7c6dff]{}

VoxMark now supports full CSS inside your documents — scoped, safe, and live.

### Scoped CSS Block

Define styles and they apply **only inside the preview** — never leaking into the editor:

:::css{
.demo-hero {
  background: linear-gradient(135deg, #7c6dff22 0%, #38d9a911 100%);
  border: 1.5px solid #7c6dff44;
  border-radius: 16px;
  padding: 28px 32px;
  text-align: center;
  margin: 8px 0;
}
.demo-hero h3 {
  font-size: 1.5rem;
  font-weight: 800;
  background: linear-gradient(90deg, #7c6dff, #38d9a9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}
.demo-hero p { color: #9ea3c0; font-size: 0.95rem; }
.demo-pulse {
  display: inline-block;
  width: 10px; height: 10px;
  background: #38d9a9;
  border-radius: 50%;
  animation: pulse-ring 1.5s ease-in-out infinite;
  margin-right: 6px;
  vertical-align: middle;
}
@keyframes pulse-ring {
  0%, 100% { box-shadow: 0 0 0 0 #38d9a966; }
  50%       { box-shadow: 0 0 0 8px #38d9a900; }
}
}

::class[demo-hero]{### ::icon[zap|1em|#7c6dff]{} Scoped CSS is Live

<span class="demo-pulse"></span> Styles above apply to **this block only** — zero leakage into the editor.}

### Inline Styles

::style[display:flex;gap:12px;flex-wrap:wrap;margin:.5em 0]{
::style[background:#7c6dff;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700]{::icon[rocket|1em|#fff]{} Primary}
::style[background:#38d9a922;color:#38d9a9;padding:10px 18px;border-radius:10px;border:1px solid #38d9a944;font-weight:700]{::icon[check|1em|#38d9a9]{} Success}
::style[background:#ef444422;color:#ef4444;padding:10px 18px;border-radius:10px;border:1px solid #ef444444;font-weight:700]{::icon[x|1em|#ef4444]{} Danger}
}

### CSS Custom Properties

::cssvar[--voxmark-brand]{#7c6dff}

After defining `::cssvar[--voxmark-brand]{#7c6dff}`, use it in any `:::css{}` block:

:::css{
.branded-box {
  border-left: 4px solid var(--voxmark-brand);
  padding: 12px 18px;
  background: color-mix(in srgb, var(--voxmark-brand) 10%, transparent);
  border-radius: 0 10px 10px 0;
  margin: 4px 0;
}
}

::class[branded-box]{This box uses `--voxmark-brand` CSS custom property defined above with `::cssvar`}

### ::b[neon]{Live CSS Playground}

A full CodePen-style split editor — edit CSS and HTML, see results instantly:

:::cssplay{/* Try editing me! */
body { font-family: system-ui, sans-serif; }

.card {
  background: linear-gradient(135deg, #7c6dff, #38d9a9);
  color: white;
  padding: 24px 28px;
  border-radius: 16px;
  max-width: 320px;
  box-shadow: 0 8px 32px #7c6dff55;
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-8px); }
}
.card h2 { font-size: 1.3rem; margin-bottom: 6px; }
.card p  { opacity: .85; font-size: .9rem; }
.tag {
  display: inline-block;
  background: rgba(255,255,255,.2);
  padding: 2px 10px;
  border-radius: 999px;
  font-size: .75rem;
  margin-top: 12px;
  backdrop-filter: blur(4px);
}
||
<div class="card">
  <h2>✦ VoxMark CSS</h2>
  <p>Edit the CSS pane and watch me change in real time.</p>
  <span class="tag">Live Preview</span>
</div>}

*Built with ❤ using Python · Flask · Mistune · VML*
"""


EXAMPLES = [
    {
        'name': 'Welcome Tour',
        'key': 'welcome',
        'source': WELCOME_DOC,
    },
    {
        'name': 'API Documentation',
        'key': 'api-docs',
        'source': r"""
# VoxMark REST API Reference

::badge[v1.0|#6c63ff] ::badge[stable|#22c55e] ::badge[JSON|#f59e0b]

## Base URL

```
http://localhost:5000/api
```

---

## Endpoints

### POST /render

Renders Markdown + VML source into HTML.

::tab[Request|Response|cURL]{
**Body (JSON)**

```json
{
  "source": "# Hello\n::alert[info]{World}"
}
```
||
```json
{
  "html": "<h1 id=\"hello\">Hello...</h1>"
}
```
||
```bash
curl -X POST http://localhost:5000/api/render \
  -H "Content-Type: application/json" \
  -d '{"source":"# Hello World"}'
```
}

### GET /health

::columns[1:2]{
**Returns**
||
```json
{"status": "ok", "version": "1.0.0", "engine": "VoxMark"}
```
}

---

## Rate Limits

::progress[60/120|Current request rate (60/120 rpm)]

::alert[warn]{API is rate-limited to **120 requests per minute** per IP. Exceeding this returns `429 Too Many Requests`.}

---

## Error Codes

| Code | Meaning                        |
|------|-------------------------------|
| 400  | Bad request / invalid input    |
| 413  | Payload too large (> 512 KB)   |
| 429  | Rate limit exceeded            |
| 500  | Internal render error          |
""",
    },
    {
        'name': 'Project README',
        'key': 'readme',
        'source': r"""
# MyProject

::badge[Python 3.12|#3b82f6] ::badge[MIT|#f59e0b] ::badge[production|#22c55e]

> A blazing-fast, zero-dependency utility library.

---

## Features

- ✅ Zero external dependencies
- ⚡ Sub-millisecond response times  
- 🔒 Cryptographically secure by default
- 🌍 Cross-platform: Windows, Linux, macOS

## Installation

```bash
pip install myproject
```

## Quick Start

```python
from myproject import Client

client = Client(api_key="your-key")
result = client.process("hello world")
print(result)
```

## Roadmap

::timeline{v0.1 Alpha::Core engine, basic API||v0.5 Beta::Plugin system, CLI tools||v1.0 Stable::Full test suite, docs, PyPI release||v2.0 Planned::WebAssembly target, browser support}

---

::callout[⭐]{Star this project on GitHub if it helps you!}
""",
    },
]
