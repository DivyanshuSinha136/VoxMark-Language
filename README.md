![VML](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VoxMark%20Language.png)

# VML — VoxMark Language

**VML** (VoxMark Language) is the widget extension system built into the VoxMark document engine. It lets you embed interactive, styled UI components directly inside any Markdown document using a clean `::widget[args]{content}` syntax — no HTML, no JavaScript, no build tools required in your source file.

VML is parsed by a hand-written Lexer → Parser → Compiler pipeline and rendered server-side into semantic HTML + CSS + WASM. The live editor previews changes instantly; `voxmark compiler --build` produces a fully standalone static site.

---

## Table of Contents

- [Syntax Basics](#syntax-basics)
- [Variables — `::var`](#variables----var)
- [Classes — `::class_def` and `@Name.prop`](#classes----class_def-and-nameprop)
- [Content Widgets](#content-widgets)
  - [Card](#card)
  - [Alert](#alert)
  - [Callout](#callout)
  - [Tabs](#tabs)
  - [Timeline](#timeline)
  - [Progress Bar](#progress-bar)
  - [Badge](#badge)
  - [Collapsible Fold](#collapsible-fold)
  - [Tooltip](#tooltip)
- [Layout Widgets](#layout-widgets)
  - [Columns](#columns)
  - [Grid](#grid)
  - [Flex](#flex)
  - [Hero](#hero)
  - [Section](#section)
  - [Box](#box)
  - [Div](#div)
  - [Center / Right](#center--right)
  - [Spacer / Divider](#spacer--divider)
- [Typography Widgets](#typography-widgets)
  - [Highlight](#highlight)
  - [Styled Bold](#styled-bold)
  - [Color](#color)
  - [Glow](#glow)
  - [Keyboard Key](#keyboard-key)
  - [Math](#math)
- [Navigation Widgets](#navigation-widgets)
  - [Sidebar](#sidebar)
  - [Router](#router)
  - [Footer](#footer)
- [Media & Embed Widgets](#media--embed-widgets)
  - [Icon](#icon)
  - [Icon Card](#icon-card)
  - [Inline SVG](#inline-svg)
  - [Embed](#embed)
- [Form Widgets](#form-widgets)
  - [Input](#input)
  - [Checkbox](#checkbox)
  - [Select](#select)
  - [Button](#button)
  - [Button Group](#button-group)
- [Control Flow Widgets](#control-flow-widgets)
  - [If](#if)
  - [Else](#else)
  - [If / Else (inline)](#if--else-inline)
- [CSS Widgets](#css-widgets)
  - [Scoped CSS Block](#scoped-css-block)
  - [CSS Playground](#css-playground)
  - [CSS Variable](#css-variable)
  - [Inline Style](#inline-style)
  - [CSS Class](#css-class)
- [Data Visualisation](#data-visualisation)
  - [Chart](#chart)
  - [Graph](#graph)
  - [Graph Playground](#graph-playground)
- [Charting](#charting)
  - [Demo Sandbox](#demo-sandbox)
- [Build-time Widgets](#build-time-widgets)
  - [Include](#include)
- [CLI Reference](#cli-reference)
- [Quick-reference Table](#quick-reference-table)

---

## Syntax Basics

VML extends Markdown with two styles of widget invocation:

```
::cmd[args]{body}       ← double colon  — most widgets
:::cmd[args]{body}      ← triple colon  — block/layout/structural widgets
```

| Part | Required | Description |
|------|----------|-------------|
| `::` or `:::` | yes | Widget opener. Triple-colon widgets are typically block-level layout containers. |
| `cmd` | yes | The widget name (case-insensitive). |
| `[args]` | depends | Pipe-separated arguments: `[arg1\|arg2\|arg3]`. Some widgets require them, some don't. |
| `{body}` | depends | Body content. Supports **Markdown**, nested `::widgets`, and `@var` references. Omit for bodyless widgets. |

### Argument separator: `|`

Multiple arguments inside `[...]` are separated by `|`:

```
::button[primary|https://example.com]{Visit}
::icon[github|1.2em|#7c6dff]{🐙}
::badge[stable|#22c55e]
```

### Body segment separator: `||`

Some widgets accept multiple body *segments* separated by `||` — for example, tabs (one segment per tab panel), columns (one segment per column), and the router (one segment per page):

```
::tab[Python|Rust]{
```python
print("hello")
```
||
```rust
println!("hello");
```
}
```

### Bodyless widgets

Some widgets take only `[args]` and no `{body}`. These never have curly braces:

```
::badge[v1.0|#7c6dff]
::progress[72/100|Completion]
::divider[]
::spacer[2em]
```

### Nesting

VML widgets nest freely inside any `{body}`:

```
::card[Example]{
  Status: ::badge[OK|#22c55e]
  Press ::kbd{Ctrl+S} to save.
  ::alert[info]{Nested alert inside a card body.}
}
```

### Markdown inside bodies

Widget bodies are fully Markdown-aware. Any Markdown that Mistune supports (CommonMark + GFM) works inside a body:

```
::callout[💡]{
**Bold**, *italic*, `inline code`, [links](https://example.com),
and even fenced code blocks all work here.
}
```

> **Exception:** the body of `::var`, `:::css`, `:::cssplay`, `::math`, `::kbd`, `::chart`, `::embed`, `::svg`, `:::demo`, `::if`, `::else`, `::ifelse`, `::router`, `::footer`, `::input`, `::checkbox`, `::select`, and `::cssvar` is treated as *raw text* (not Markdown) because those widgets need their body content unmodified.

---

## Variables — `::var`

Define a reusable text value once and reference it anywhere with `@name`.

```
::var[author]{Divyanshu Sinha}
::var[version]{2.0.0}
::var[repo]{https://github.com/DivyanshuSinha136}

Built by **@author** — VoxMark v@version.
[Source code](@repo)
```

- Variable names are case-sensitive identifiers.
- Values can contain any text including spaces and special characters.
- Re-defining a variable replaces its previous value.
- `@name` references are resolved after all widget rendering, so a variable defined anywhere in the document is available everywhere.

---

## Classes — `::class_def` and `@Name.prop`

Define an **object-style namespace** of named properties and reference them with dot notation throughout the document.

```
::class_def[School]{
  name:Springfield Elementary
  ||address:742 Evergreen Terrace, Springfield
  ||founded:1953
  ||principal:Principal Skinner
  ||website:https://springfield-elem.edu
}

The school is **@School.name**, founded in @School.founded.
Address: @School.address
Principal: @School.principal — [Website](@School.website)
```

### Syntax rules

| Rule | Detail |
|------|--------|
| Body format | Each `\|\|`-separated segment is `key:value` |
| Key | Any word characters: `[A-Za-z0-9_]+` |
| Value | Everything after the first `:` (may contain colons, spaces, URLs, etc.) |
| ClassName | Convention: start with a capital letter. `re.sub(r'[^\w]', '', name)` for safety. |
| Unknown ref | `@School.unknown` is left unchanged — safe to use conditionally |
| Re-definition | Replaces all properties of that class |
| Visibility | Emits an invisible `<meta class="vml-class-def">` tag — no visible output |

### Dot-ref vs plain-var

| Syntax | Resolves |
|--------|---------|
| `@School.name` | Class property (resolved first) |
| `@author` | Simple var (no dot — resolved after class refs) |

Class properties work inside any widget body, argument, or plain text.

---

## Content Widgets

### Card

A rounded content card with an optional title bar.

```
::card[🚀 Card Title]{
Body content here. Supports **Markdown**, ::badge[tags|#7c6dff], and nested widgets.
}
```

- **`[arg0]`** — card title (optional, leave empty for a title-less card)
- **`{body}`** — card body, fully Markdown-rendered

```
::card[]{No title — just body content.}
::card[With Icon ::icon[rocket|.9em|#f59e0b]{}]{Body text}
```

---

### Alert

A status alert box. Four built-in styles.

```
::alert[success]{Your document saved successfully.}
::alert[info]{This is an informational note.}
::alert[warn]{Something needs your attention.}
::alert[error]{An error occurred. Check the logs.}
```

- **`[arg0]`** — style: `success` · `info` · `warn` · `error`
- **`{body}`** — alert message, Markdown-rendered

---

### Callout

A highlighted callout / tip box with a leading emoji icon.

```
::callout[💡]{**Pro Tip:** You can use `::var[name]{value}` to define
reusable values and reference them with `@name`.}

::callout[⚠]{Be careful when nesting more than 3 levels of widgets.}
::callout[🔗]{Check the [full docs](https://github.com/DivyanshuSinha136).}
```

- **`[arg0]`** — emoji or short icon (default: `💡`)
- **`{body}`** — callout content, Markdown-rendered

---

### Tabs

A tabbed panel. Tab labels go in `[args]`, tab content segments in `{body}` separated by `||`.

```
::tab[Python|JavaScript|Rust]{
```python
def hello(name: str) -> str:
    return f"Hello, {name}!"
```
||
```javascript
const hello = name => `Hello, ${name}!`;
```
||
```rust
fn hello(name: &str) -> String {
    format!("Hello, {}!", name)
}
```
}
```

- **`[arg0|arg1|…]`** — tab labels (must match number of `||` segments in body)
- **`{seg0||seg1||…}`** — one content segment per tab, Markdown-rendered

---

### Timeline

A vertical event timeline. Each item is `Title::Description`, separated by `||`.

```
::timeline{
  Project Kickoff::Started VoxMark as a production-grade document engine.
  ||v1.0 Released::Shipped Markdown + 26 VML widgets with live preview.
  ||v2.0::Added sidebar, router, footer, includes, class system, and forms.
  ||You Are Here::Explore, edit, and create!
}
```

- **`{body}`** — each segment is `Title::Description` (separated by `||`)
- The `::` inside body text is the field separator between title and description; it does *not* trigger a widget parse

---

### Progress Bar

An animated progress bar with an optional label.

```
::progress[72/100|Project Completion]
::progress[3/5|Milestones]
::progress[1/1|Tests Passing]
```

- **`[value/max|label]`** — current value, maximum value, and display label
- Bodyless — no `{...}` required
- Percentage is computed as `(value / max) × 100`

---

### Badge

An inline pill badge.

```
Status: ::badge[stable|#22c55e]
Version: ::badge[v2.0|#7c6dff]
License: ::badge[MIT|#f59e0b]
Platform: ::badge[Python 3.12|#3b82f6]
```

- **`[label|colour]`** — label text and background hex colour
- Bodyless — no `{...}` required
- Inline element — can appear mid-sentence

---

### Collapsible Fold

A `<details>` / `<summary>` collapsible section. Uses triple-colon (`:::`).

```
:::fold[Click to expand — Advanced Options]{
### Variable System

Define once, use everywhere:
```
::var[author]{Divyanshu Sinha}
```

### Nested Widgets

Everything works inside a fold:

::alert[info]{Even alerts.}
::progress[80/100|Even progress bars.]
}
```

- **`[arg0]`** — summary / trigger label
- **`{body}`** — hidden content, fully Markdown + VML rendered

---

### Tooltip

An inline element with a hover tooltip.

```
VoxMark uses ::tooltip[LEB128|Unsigned Little-Endian Base-128 variable-length encoding]{LEB128}
encoding in its WASM binary output.
```

- **`[tip]`** — tooltip text shown on hover
- **`{body}`** — the visible anchor text

---

## Layout Widgets

### Columns

A responsive multi-column layout. Columns use `||` to separate content.

```
::columns[1:1]{
**Left column**

Full Markdown here — lists, code, widgets, anything.
||
**Right column**

::alert[info]{Even nested widgets.}
}
```

- **`[ratio]`** — colon-separated flex ratios, e.g. `1:1`, `2:1`, `1:1:1`, `3:1`
- **`{col0||col1||…}`** — one segment per column
- Wraps on mobile automatically

```
::columns[2:1]{
Main content (takes 2/3 width)
||
Sidebar content (takes 1/3 width)
}
```

---

### Grid

A CSS grid container. Uses triple-colon.

```
:::grid[3|16px]{
::card[Card 1]{Content}
||
::card[Card 2]{Content}
||
::card[Card 3]{Content}
}
```

- **`[cols|gap]`** — number of columns (or CSS `grid-template-columns` value) and gap size
- **`{cell0||cell1||…}`** — one segment per cell

---

### Flex

A CSS flex container. Uses triple-colon.

```
:::flex[12px|center|flex-start|wrap]{
::badge[Python|#3b82f6]
||
::badge[NASM|#f59e0b]
||
::badge[Flask|#22c55e]
}
```

- **`[gap|align-items|justify-content|flex-wrap]`** — all optional, pipe-separated
- **`{item0||item1||…}`** — flex items

---

### Hero

A full-width hero section with configurable background and alignment. Uses triple-colon.

```
:::hero[#13162a|center|400px]{
# Welcome to VoxMark

The document engine built from **first principles**.

:::btngroup{::button[primary|#]{Get Started}||::button[ghost|#]{Learn More}}
}
```

- **`[bg-colour|text-align|min-height]`** — background colour, `left`/`center`/`right`, minimum height
- **`{body}`** — hero content, Markdown + VML rendered

---

### Section

A full-width content section with optional title and subtitle. Uses triple-colon.

```
:::section[Features|Everything you need|center]{
::columns[1:1:1]{
::card[Fast]{Sub-millisecond rendering.}
||
::card[Secure]{XSS scanning built in.}
||
::card[Extensible]{53+ widget types.}
}
}
```

- **`[title|subtitle|align]`** — all optional

---

### Box

A styled container box with configurable variant. Uses triple-colon.

```
:::box[info]{
This is an info box. Useful for highlighting important content.
}
```

---

### Div

A generic `<div>` wrapper with custom class, id, or style. Uses triple-colon.

```
:::div[my-custom-class|my-id|color:red;font-size:1.2em]{
Content with custom styling applied.
}
```

- **`[class|id|style]`** — all optional, pipe-separated

---

### Center / Right

Align block content.

```
::center{This text and ::badge[content|#7c6dff] are centered.}

::right{Right-aligned text.}
```

---

### Spacer / Divider

Add whitespace or a horizontal rule.

```
::spacer[2em]         ← vertical whitespace of 2em

::divider[]           ← default styled HR
::divider[dashed]     ← dashed style
::divider[dotted]     ← dotted style
::divider[gradient]   ← gradient fade
```

Both are bodyless — no `{...}`.

---

## Typography Widgets

### Highlight

Highlighted / marked text with colour variants.

```
Normal text, then ::hl[yellow]{important}, ::hl[green]{success},
::hl[pink]{warning}, ::hl[blue]{info}, ::hl[orange]{note}, ::hl[purple]{vml}.
```

- **`[colour]`** — `yellow` · `green` · `pink` · `blue` · `orange` · `purple`
- **`{text}`** — inline text to highlight

---

### Styled Bold

Bold text with special rendering styles.

```
::b[gradient]{Gradient}   — multicolour gradient fill
::b[outline]{Outline}     — transparent with a stroke
::b[shadow]{Shadow}       — layered drop shadow
::b[neon]{Neon}           — glowing neon effect
::b[stamp]{STAMP}         — uppercase bordered stamp
::b[underline]{Underline} — accent underline
::b[mono]{mono}           — monospace code-style bold
```

- **`[style]`** — one of the above styles
- **`{text}`** — the bold text content

---

### Color

Inline text with a custom colour.

```
::color[#ef4444]{Red text}  ::color[#22c55e]{Green text}  ::color[#f59e0b]{Amber text}
```

- **`[hex]`** — any CSS colour value (hex, named, rgb, etc.)
- **`{text}`** — text to colour

---

### Glow

Glowing text with a custom glow colour.

```
::glow[#7c6dff]{VoxMark glows in the dark.}
::glow[#38d9a9]{Teal glow}
```

- **`[colour]`** — CSS colour for the glow
- **`{text}`** — text to apply the glow effect to

---

### Keyboard Key

Render keyboard shortcuts as styled `<kbd>` elements.

```
Press ::kbd{Ctrl+S} to save.
Press ::kbd{Ctrl+Enter} to render.
Press ::kbd{⌘+K} to open command palette.
```

- **`{body}`** — key combination text (raw, not Markdown)

---

### Math

Render a LaTeX / KaTeX expression.

```
::math{E = mc^2}
::math{\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}}
::math{\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}}
```

- **`{body}`** — LaTeX expression (raw, processed by KaTeX)
- KaTeX must be loaded (included automatically in `--build` output)

---

## Navigation Widgets

### Sidebar

A slide-in navigation sidebar with a floating toggle button. Uses triple-colon.

```
:::sidebar[My Portfolio|left|260px]{
  Site Name
  ||Home::#home
  ||About::#about
  ||Projects::#projects
  ||---
  ||Contact::#contact
  ||::badge[v2.0|#7c6dff]
}
```

**Arguments** (`[Title|side|width]`):

| Arg | Default | Description |
|-----|---------|-------------|
| Title | `Menu` | Shown in the sidebar header |
| side | `left` | `left` or `right` |
| width | `260px` | CSS width of the sidebar panel |

**Body segment formats** (separated by `||`):

| Pattern | Renders as |
|---------|-----------|
| `Label::href` | Nav link — `<a class="vml-sidebar-link">` |
| `---` | Horizontal divider |
| Plain text | Section heading |
| `::widget{...}` | Raw widget block inside the sidebar |

- Clicking the overlay or pressing `Escape` closes the sidebar
- Multiple sidebars on one page are independent (each has a unique UID)
- The `☰` toggle button is position-fixed at `top:16px` on the chosen edge

---

### Router

A hash-based single-page router with auto-generated tab navigation.

```
::router[home]{
  home:Home::# Welcome
  Body of the home page — full Markdown + VML.

  ||about:About::# About
  About page content here.

  ||projects:Projects::# Projects
  ::card[VoxMark]{A compiler built from scratch.}
}
```

**`[default_page_id]`** — the page shown on first load (defaults to first page).

**Body segment format:** each `||` segment is `page_id:Display Title::page body`.

| Field | Description |
|-------|-------------|
| `page_id` | URL-safe identifier, used as `#hash` |
| `Display Title` | Shown in the nav bar and `document.title` |
| `page body` | Full VML + Markdown content for this page |

- Direct URL navigation: visiting `page.html#about` loads the `about` page immediately
- `history.replaceState` updates the URL hash without a page reload
- Pages fade in with a CSS animation on each switch
- Nested widgets (cards, badges, progress bars, forms, etc.) work inside every page

**Combined with `::include` for multi-file sites:**

```
::router[home]{
  home:Home::     ::include[./sections/home.vml]
  ||about:About:: ::include[./sections/about.vml]
  ||work:Work::   ::include[./sections/work.vml]
}
```

---

### Footer

A site footer with an optional multi-column layout and copyright bar.

```
::footer[© 2025 Divyanshu Sinha|#7c6dff]{
  **VoxMark**
  A custom Markdown + VML engine.
  ::badge[Open Source|#22c55e]
  ||
  **Navigation**
  [Home](#home) · [About](#about) · [Projects](#projects)
  ||
  **Connect**
  ::icon[github|1em|#7c6dff]{} [GitHub](https://github.com/DivyanshuSinha136)
  ::icon[mail|1em|#38d9a9]{} [Email](mailto:you@example.com)
}
```

**Arguments** (`[copyright|accent]`):

| Arg | Default | Description |
|-----|---------|-------------|
| copyright | *(empty)* | Text for the bottom copyright bar |
| accent | `#7c6dff` | Gradient colour for the top border |

**Body:**
- **Single segment** → full-width centered block
- **Multiple `||` segments** → flex columns, wrapping on mobile

Each column renders its own mini VML + inline-Markdown pass, so badges, icons, links, and bold/italic text all work inside footer columns.

---

## Media & Embed Widgets

### Icon

An inline SVG icon from the built-in icon set.

```
::icon[github|1.2em|#7c6dff]{🐙}
::icon[rocket|1em|#f59e0b]{}
::icon[check-circle|1em|#22c55e]{} Done
```

- **`[name|size|colour]`** — icon name, CSS size, CSS colour (all after first are optional)
- **`{fallback}`** — emoji or text shown if the icon name is not recognised

**Available icons (43 total):**

```
arrow-right   arrow-left    arrow-up      arrow-down    check         check-circle
x             x-circle      info          warn          star          heart
code          copy          download      upload        search        settings
user          users         home          mail          bell          lock
unlock        eye           edit          trash         plus          plus-circle
minus         external      link          github        moon          sun
zap           box           layers        cpu           terminal      package
rocket
```

---

### Icon Card

A card with a large icon, title, and description text.

```
::iconcard[rocket|Fast Render]{Sub-millisecond VML transforms.}
::iconcard[lock|Secure]{XSS scanning and rate limiting built in.}
::iconcard[layers|Extensible]{53+ widget types and growing.}
```

- **`[icon-name|title]`** — icon from the built-in set and card title
- **`{body}`** — description text

Best used inside `:::grid` or `::columns` for a feature-cards layout.

---

### Inline SVG

Render raw SVG directly in the document. Uses triple-colon.

```
:::svg{
<svg viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#7c6dff"/>
      <stop offset="100%" style="stop-color:#38d9a9"/>
    </linearGradient>
  </defs>
  <rect width="200" height="60" rx="10" fill="#13162a"/>
  <text x="16" y="38" font-size="22" font-weight="bold" fill="url(#g)">VoxMark</text>
</svg>
}
```

- **`{body}`** — raw SVG markup, sanitised server-side
- No `[args]` needed

---

### Embed

Embed external content of many types.

```
::embed[youtube]{https://www.youtube.com/watch?v=dQw4w9WgXcQ}
::embed[github]{https://github.com/DivyanshuSinha136/VoxMark}
::embed[spotify]{https://open.spotify.com/track/...}
::embed[codepen]{https://codepen.io/pen/...}
::embed[map]{https://maps.google.com/...}
::embed[pdf]{/docs/spec.pdf}
::embed[audio]{/assets/music.mp3}
::embed[image]{https://example.com/photo.jpg}
::embed[site]{https://example.com}
```

- **`[type]`** — `youtube` · `github` · `spotify` · `codepen` · `map` · `pdf` · `audio` · `image` · `site`
- **`{src}`** — the URL or path to embed

---

## Form Widgets

### Input

A styled form input field.

```
::input[text|Enter your name|inp-name]{Full Name}
::input[email|you@example.com|inp-email]{Email Address}
::input[password|••••••••|inp-pw]{Password}
::input[number|0|score|50|0|100|1]{Score (0–100)}
::input[date||dob]{Date of Birth}
::input[range||brightness|75|0|100]{Brightness}
::input[color||accent|#7c6dff]{Accent Colour}
::input[file||upload]{Upload File}
```

**Arguments** (`[type|placeholder|id|default|min|max|step]`):

| Arg | Default | Description |
|-----|---------|-------------|
| type | `text` | Input type (see list below) |
| placeholder | — | Placeholder text |
| id | auto | Element `id` and `name` |
| default | — | Initial value |
| min | — | Minimum (for `number`, `range`) |
| max | — | Maximum (for `number`, `range`) |
| step | — | Step increment (for `number`, `range`) |

**`{body}`** — visible label text (above the input)

**Supported types:** `text` · `email` · `password` · `number` · `url` · `tel` · `search` · `date` · `datetime-local` · `time` · `range` · `color` · `file`

Range inputs get a live numeric readout. Color inputs get a swatch preview.

---

### Checkbox

A styled checkbox with a label.

```
::checkbox[agree|yes]{I agree to the terms and conditions.}
::checkbox[newsletter|yes|checked]{Subscribe to newsletter (pre-ticked)}
```

**Arguments** (`[id|value|checked]`):

| Arg | Default | Description |
|-----|---------|-------------|
| id | auto | Element `id` and `name` |
| value | `on` | Form submission value |
| checked | — | Write `checked` to pre-tick |

**`{body}`** — checkbox label text

---

### Select

A styled dropdown select.

```
::select[country|IN|Country]{
  US:United States|UK:United Kingdom|IN:India|JP:Japan|DE:Germany
}

::select[size||T-Shirt Size]{S|M|L|XL|XXL}
```

**Arguments** (`[id|default|label]`):

| Arg | Default | Description |
|-----|---------|-------------|
| id | auto | Element `id` and `name` |
| default | — | Pre-selected value |
| label | — | Visible label above the select |

**`{body}`** — pipe-separated options:
- Plain: `Small` (value = label)
- With value: `S:Small` (value `S`, displays `Small`)

---

### Button

A styled button / link.

```
::button[primary|https://github.com]{Visit GitHub}
::button[secondary|#about]{Learn More}
::button[ghost|mailto:you@example.com]{Send Email}
::button[outline|#]{Read Docs}
::button[danger|#delete]{Delete}
::button[success|#]{Confirm}
```

**Arguments** (`[style|action]`):

| Arg | Default | Description |
|-----|---------|-------------|
| style | `primary` | `primary` · `secondary` · `ghost` · `outline` · `danger` · `success` |
| action | `#` | `href` value — URL, `#hash`, `mailto:`, `tel:`, or `javascript:` |

**`{body}`** — button label, supports inline VML like `::icon` and `::badge`

---

### Button Group

A group of buttons rendered inline. Uses triple-colon.

```
:::btngroup{
  ::button[primary|#]{Get Started}
  ||::button[ghost|#]{Learn More}
  ||::button[outline|https://github.com]{GitHub}
}
```

- **`{button0||button1||…}`** — each segment is a `::button` widget or any inline content

---

## Control Flow Widgets

All control-flow widgets are **client-side** — the condition is evaluated in the browser using `Function("return (expr)")()` with a character-class safety filter. They are evaluated once at page-load.

### If

Show content when a JavaScript expression is truthy.

```
::if[window.innerWidth > 768]{Wide-screen layout — only visible on desktop.}

::if[navigator.language.startsWith('en')]{English content.}

::if[document.documentElement.dataset.theme === 'dark']{Dark mode content.}
```

- **`[condition]`** — JS expression (sanitised to `[A-Za-z0-9_.\\s<>=!&|()]`)
- **`{body}`** — content shown when condition is truthy

---

### Else

Show content when the same expression is **falsy**. Pair with a preceding `::if`.

```
::if[window.innerWidth > 768]{Wide layout.}
::else[window.innerWidth > 768]{Narrow / mobile layout.}
```

- Uses the same condition string as the matching `::if`

---

### If / Else (inline)

Compact inline branch — shows one of two segments based on a condition.

```
::ifelse[navigator.onLine]{
  You are **online** — live features active.
  ||
  You are **offline** — some features unavailable.
}
```

- **`{then||else}`** — two segments: first shown if truthy, second if falsy

---

## CSS Widgets

### Scoped CSS Block

Define CSS that applies to the current document scope. Uses triple-colon.

```
:::css{
.my-box {
  background: linear-gradient(135deg, #7c6dff22, #38d9a911);
  border: 1px solid #7c6dff44;
  border-radius: 12px;
  padding: 20px 24px;
}
.my-box h3 {
  color: #7c6dff;
  margin: 0 0 8px;
}
}

::class[my-box]{### Scoped styles applied here

This block uses the styles defined above.}
```

- **`{body}`** — raw CSS (not processed through Markdown)
- Styles are injected via a `<style>` tag in the page

---

### CSS Playground

A live split-editor showing CSS and HTML side-by-side with instant preview. Uses triple-colon.

```
:::cssplay{
.card {
  background: linear-gradient(135deg, #7c6dff, #38d9a9);
  padding: 24px; border-radius: 16px; color: white;
}
||
<div class="card">
  <h2>Live Preview</h2>
  <p>Edit the CSS pane to see changes instantly.</p>
</div>
}
```

- **`{css||html}`** — two segments: CSS in the first, HTML in the second

---

### CSS Variable

Define a CSS custom property (`--variable`) for the document scope.

```
::cssvar[--brand]{#7c6dff}
::cssvar[--accent2]{#38d9a9}
::cssvar[--gap]{16px}
```

Then use it in any `:::css{}` block:

```
:::css{
.branded {
  border-left: 4px solid var(--brand);
  background: color-mix(in srgb, var(--brand) 10%, transparent);
}
}
```

- **`[--property-name]`** — the CSS custom property name (must start with `--`)
- **`{value}`** — the property value

---

### Inline Style

Apply arbitrary inline CSS to a block of content.

```
::style[display:flex;gap:12px;flex-wrap:wrap;margin:.5em 0]{
  ::style[background:#7c6dff;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700]{Primary}
  ::style[background:#22c55e22;color:#22c55e;padding:10px 18px;border-radius:10px;border:1px solid #22c55e44]{Success}
}
```

- **`[css-properties]`** — semicolon-separated CSS property declarations
- **`{body}`** — content to wrap in the styled container

---

### CSS Class

Apply one or more CSS class names to a block of content.

```
::class[my-box hero-card]{
### Scoped Class Applied

Content inside this div has `class="my-box hero-card"` applied.
}
```

- **`[class-names]`** — space-separated class name(s)
- **`{body}`** — content, Markdown-rendered

---

## Data Visualisation

### Chart

A Chart.js chart powered by a JSON data payload.

```
::chart[bar]{
{
  "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
  "datasets": [{
    "label": "Revenue ($k)",
    "data": [42, 58, 37, 71, 63],
    "backgroundColor": ["#7c6dff","#38d9a9","#f59e0b","#ef4444","#3b82f6"]
  }]
}
}
```

- **`[type]`** — `bar` · `line` · `pie` · `doughnut` · `radar` · `polarArea`
- **`{body}`** — Chart.js-compatible JSON `{ labels, datasets }` object
- Chart.js must be loaded (included automatically in `--build` output)

---

### Graph

A rich server-side data graph with built-in themes.

```
::graph[bar|Monthly Revenue|purple|280px]{
{
  "labels": ["Jan","Feb","Mar","Apr"],
  "data":   [42, 58, 37, 71]
}
}
```

- **`[type|title|palette|height]`** — chart type, display title, colour palette, container height
- **`{body}`** — simplified JSON `{ labels, data }` object

---

### Graph Playground

An interactive graph editor. Uses triple-colon.

```
:::graphplay{
{
  "type": "line",
  "labels": ["Mon","Tue","Wed","Thu","Fri"],
  "data":   [5, 12, 8, 19, 14]
}
}
```

---

### Demo Sandbox

A live HTML/CSS sandbox. Uses triple-colon.

```
:::demo{
<div style="background:linear-gradient(135deg,#7c6dff,#38d9a9);padding:32px;border-radius:16px;color:white;text-align:center">
  <h2>✦ Live Demo</h2>
  <p>This HTML is editable and renders live.</p>
</div>
}
```

- **`{body}`** — raw HTML rendered in a sandboxed `<iframe>`
- The source is shown in an editable textarea; clicking ▶ Run re-renders

---

## Build-time Widgets

### Include

Read another `.vml` file from disk and inline its fully-rendered output here.

```
::include[./header.vml]
::include[./sections/about.vml]
::include[../shared/footer.vml]
```

- **`[path]`** — path **relative to the current source file**
- Allowed extensions: `.vml` · `.md` · `.txt`
- Processed at **compile time** by `voxmark compiler --build`
- In the live editor (`/api/render`), includes render as empty placeholders since there is no filesystem context
- **Circular includes** are detected and skipped with an HTML comment
- **Nesting** up to 16 levels deep is supported
- Missing files emit an HTML comment instead of an error

**Multi-file project example:**

```
my-site/
  index.vml
  sections/
    home.vml
    about.vml
    contact.vml
```

`index.vml`:
```
:::sidebar[My Site]{Home::#home||About::#about||Contact::#contact}

::router[home]{
  home:Home::  ::include[./sections/home.vml]
  ||about:About:: ::include[./sections/about.vml]
  ||contact:Contact:: ::include[./sections/contact.vml]
}

::footer[© 2025]{Built with **VoxMark**}
```

Build with:
```sh
voxmark compiler --build index.vml -o build/
```

---

## CLI Reference

```
voxmark compiler --build <input> -o <build-dir>
```

| Flag | Description |
|------|-------------|
| `--build` | Required. Compile to HTML + CSS + WASM + JS loader. |
| `input` | Source `.vml` / `.md` file or directory. |
| `-o / --output` | Output directory (default: `build/`). |
| `--title` | Override HTML `<title>`. |
| `--no-wasm` | Skip `.wasm` / `loader.js` output. |
| `--no-wat` | Skip `debug.wat` output. |

```
voxmark server <build-dir> [--port PORT] [--host HOST] [--open]
voxmark lint [input]
voxmark format [input] [-o output] [-i]
voxmark ast [input] [--json]
voxmark init [directory]
voxmark watch [input] -o <build-dir> [--port PORT]
voxmark version
```

**Global flags:** `--verbose / -v` · `--quiet / -q` · `--no-color`

---

## Quick-reference Table

| Widget | Syntax | Triple? | Bodyless? |
|--------|--------|---------|-----------|
| Alert | `::alert[type]{msg}` | — | — |
| Badge | `::badge[label\|colour]` | — | ✓ |
| Bold styled | `::b[style]{text}` | — | — |
| Box | `:::box[variant]{content}` | ✓ | — |
| Button | `::button[style\|href]{label}` | — | — |
| Button group | `:::btngroup{::button\|\|…}` | ✓ | — |
| Callout | `::callout[emoji]{text}` | — | — |
| Card | `::card[title]{body}` | — | — |
| Center | `::center{content}` | — | — |
| Chart | `::chart[type]{json}` | — | — |
| Checkbox | `::checkbox[id\|val\|checked]{label}` | — | — |
| Class (apply) | `::class[names]{body}` | — | — |
| Class (define) | `::class_def[Name]{k:v\|\|k:v}` | — | — |
| Color | `::color[#hex]{text}` | — | — |
| Columns | `::columns[1:1]{col\|\|col}` | — | — |
| CSS block | `:::css{…}` | ✓ | — |
| CSS class | `::class[names]{content}` | — | — |
| CSS playground | `:::cssplay{css\|\|html}` | ✓ | — |
| CSS variable | `::cssvar[--name]{value}` | — | — |
| Demo sandbox | `:::demo{html}` | ✓ | — |
| Div | `:::div[class\|id\|style]{content}` | ✓ | — |
| Divider | `::divider[style]` | — | ✓ |
| Else | `::else[cond]{content}` | — | — |
| Embed | `::embed[type]{url}` | — | — |
| Flex | `:::flex[gap\|…]{item\|\|item}` | ✓ | — |
| Fold | `:::fold[title]{body}` | ✓ | — |
| Footer | `::footer[copy\|accent]{col\|\|col}` | — | — |
| Glow | `::glow[colour]{text}` | — | — |
| Graph | `::graph[type\|title\|palette\|h]{json}` | — | — |
| Graph playground | `:::graphplay{json}` | ✓ | — |
| Grid | `:::grid[cols\|gap]{cell\|\|cell}` | ✓ | — |
| Hero | `:::hero[bg\|align\|h]{content}` | ✓ | — |
| Highlight | `::hl[colour]{text}` | — | — |
| Icon | `::icon[name\|size\|colour]{fallback}` | — | — |
| Icon card | `::iconcard[icon\|title]{desc}` | — | — |
| If | `::if[cond]{content}` | — | — |
| If/else | `::ifelse[cond]{then\|\|else}` | — | — |
| Include | `::include[./file.vml]` | — | ✓ |
| Input | `::input[type\|…]{label}` | — | — |
| Keyboard key | `::kbd{key combo}` | — | — |
| Math | `::math{LaTeX}` | — | — |
| Progress | `::progress[val/max\|label]` | — | ✓ |
| Right-align | `::right{content}` | — | — |
| Router | `::router[default]{id:Title::body\|\|…}` | — | — |
| Section | `:::section[title\|sub\|align]{body}` | ✓ | — |
| Select | `::select[id\|default\|label]{opts}` | — | — |
| Sidebar | `:::sidebar[title\|side\|w]{nav}` | ✓ | — |
| Spacer | `::spacer[size]` | — | ✓ |
| Style (inline) | `::style[css]{content}` | — | — |
| SVG | `:::svg{<svg>…</svg>}` | ✓ | — |
| Tab | `::tab[A\|B]{body\|\|body}` | — | — |
| Timeline | `::timeline{Title::Desc\|\|…}` | — | — |
| Tooltip | `::tooltip[tip text]{anchor}` | — | — |
| Variable | `::var[name]{value}` | — | — |

---

*VoxMark Language — designed and built by Divyanshu Sinha*
*Source: [github.com/DivyanshuSinha136](https://github.com/DivyanshuSinha136)*
