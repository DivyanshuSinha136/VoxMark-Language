![VML](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VoxMark%20Language.png)

# VML — VoxMark Language

**Version:** 1.0.0

VML (**VoxMark Language**) is a declarative programming language for building interactive web applications and documents. It combines component-based UI, data binding, conditional rendering, scoped styling, reusable object definitions, routing, and compilation to HTML, CSS, and WebAssembly through the **VoxMark compiler**.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Syntax Basics](#syntax-basics)
  - [Widget Anatomy](#widget-anatomy)
  - [Argument Separator `|`](#argument-separator-)
  - [Body Segment Separator `||`](#body-segment-separator-)
  - [Bodyless Widgets](#bodyless-widgets)
  - [Nesting](#nesting)
  - [Markdown Inside Bodies](#markdown-inside-bodies)
- [Variables](#variables)
- [Classes](#classes)
- [Widget Reference](#widget-reference)
  - [Content Widgets](#content-widgets)
  - [Layout Widgets](#layout-widgets)
  - [Typography Widgets](#typography-widgets)
  - [Navigation Widgets](#navigation-widgets)
  - [Media & Embed Widgets](#media--embed-widgets)
  - [Form Widgets](#form-widgets)
  - [Control Flow Widgets](#control-flow-widgets)
  - [CSS Widgets](#css-widgets)
  - [Data Visualisation](#data-visualisation)
  - [Build-time Widgets](#build-time-widgets)
- [Multi-file Projects](#multi-file-projects)
- [CLI Reference](#cli-reference)
- [Quick Reference Table](#quick-reference-table)
- [License](#license)

---

## Features

- **Component-based UI** — 50+ built-in widgets covering content, layout, typography, navigation, media, forms, control flow, styling, and data visualisation.
- **Data binding** — reusable variables (`::var`) and object-style classes (`::class_def`) referenced anywhere with `@name` / `@Name.prop`.
- **Conditional rendering** — client-side `::if` / `::else` / `::ifelse` widgets evaluated from JavaScript expressions.
- **Scoped styling** — inline styles, CSS classes, scoped `:::css` blocks, and CSS custom properties via `::cssvar`.
- **Routing** — hash-based single-page router (`::router`) with auto-generated navigation.
- **Compilation targets** — HTML, CSS, and WebAssembly (WASM), produced by the VoxMark compiler.
- **Multi-file projects** — compose full sites from separate `.vml` files using `::include`.

---

## Installation

Install VoxMark Language using the Python Package Manager (pip):

```bash
pip install voxmark
```

---

## Quick Start

**1. Create a project**

```bash
voxmark init my-project
```

**2. Change into the project directory**

```bash
cd my-project
```

**3. Build the project**

```bash
voxmark compiler --build index.vml -o build/
```

Optionally set a title:

```bash
voxmark compiler --build index.vml -o build/ --title My-Project
```

**4. Preview the build**

Open `build/index.html` directly, or run the VoxMark server:

```bash
voxmark server build/
```

Choose a port:

```bash
voxmark server --port 7080 build/
```

Bind a host and port:

```bash
voxmark server --host 0.0.0.0 --port 7080 build/
```

---

## Syntax Basics

### Widget Anatomy

```
::cmd[args]{body}       ← double colon  — most widgets
:::cmd[args]{body}      ← triple colon  — block/layout/structural widgets
```

| Part | Required | Description |
|---|---|---|
| `::` or `:::` | yes | Widget opener. Triple-colon widgets are typically block-level layout containers. |
| `cmd` | yes | The widget name (case-insensitive). |
| `[args]` | depends | Pipe-separated arguments: `[arg1\|arg2\|arg3]`. Some widgets require them, some don't. |
| `{body}` | depends | Body content. Supports Markdown, nested `::widgets`, and `@var` references. Omit for bodyless widgets. |

### Argument Separator `|`

Multiple arguments inside `[...]` are separated by `|`:

```
::button[primary|https://example.com]{Visit}
::icon[github|1.2em|#7c6dff]{🐙}
::badge[stable|#22c55e]
```

### Body Segment Separator `||`

Some widgets accept multiple body segments separated by `||` — for example, tabs (one segment per tab panel), columns (one segment per column), and the router (one segment per page):

```
::tab[Python|Rust]{
python
||
rust
}
```

### Bodyless Widgets

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

### Markdown Inside Bodies

Widget bodies are fully Markdown-aware. Any Markdown that Mistune supports (CommonMark + GFM) works inside a body:

```
::callout[💡]{
**Bold**, *italic*, `inline code`, [links](https://example.com),
and even fenced code blocks all work here.
}
```

> **Exception:** the body of `::var`, `:::css`, `:::cssplay`, `::math`, `::kbd`, `::chart`, `::embed`, `::svg`, `:::demo`, `::if`, `::else`, `::ifelse`, `::router`, `::footer`, `::input`, `::checkbox`, `::select`, and `::cssvar` is treated as raw text (not Markdown) because those widgets need their body content unmodified.

---

## Variables

Define a reusable text value once and reference it anywhere with `@name`.

```
::var[author]{Divyanshu Sinha}
::var[version]{2.0.0}
::var[repo]{https://github.com/DivyanshuSinha136}

Built by **@author** — VoxMark v@version.
[Source code](@repo)
```

**Rules:**
- Variable names are case-sensitive identifiers.
- Values can contain any text including spaces and special characters.
- Re-defining a variable replaces its previous value.
- `@name` references are resolved after all widget rendering, so a variable defined anywhere in the document is available everywhere.

---

## Classes

Define an object-style namespace of named properties and reference them with dot notation throughout the document.

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

**Syntax rules:**

| Rule | Detail |
|---|---|
| Body format | Each `\|\|`-separated segment is `key:value` |
| Key | Any word characters: `[A-Za-z0-9_]+` |
| Value | Everything after the first `:` (may contain colons, spaces, URLs, etc.) |
| ClassName | Convention: start with a capital letter. `re.sub(r'[^\w]', '', name)` for safety. |
| Unknown ref | `@School.unknown` is left unchanged — safe to use conditionally |
| Re-definition | Replaces all properties of that class |
| Visibility | Emits an invisible `<meta class="vml-class-def">` tag — no visible output |

**Dot-ref vs plain-var:**

| Syntax | Resolves |
|---|---|
| `@School.name` | Class property (resolved first) |
| `@author` | Simple var (no dot — resolved after class refs) |

Class properties work inside any widget body, argument, or plain text.

---

## Widget Reference

### Content Widgets

| Widget | Description |
|---|---|
| **Card** | A rounded content card with an optional title bar. `::card[title]{body}` |
| **Alert** | A status alert box with four styles: `success`, `info`, `warn`, `error`. `::alert[type]{msg}` |
| **Callout** | A highlighted callout / tip box with a leading emoji icon. `::callout[emoji]{body}` |
| **Tabs** | A tabbed panel. Labels go in `[args]`, content segments in `{body}` separated by `\|\|`. `::tab[A\|B]{seg0\|\|seg1}` |
| **Timeline** | A vertical event timeline. Each item is `Title::Description`, segments separated by `\|\|`. `::timeline{...}` |
| **Progress Bar** | An animated progress bar with an optional label. `::progress[value/max\|label]` (bodyless) |
| **Badge** | An inline pill badge. `::badge[label\|colour]` (bodyless) |
| **Collapsible** | A `<details>`/`<summary>` collapsible section. Uses triple-colon. `:::fold[summary]{body}` |
| **Tooltip** | An inline element with a hover tooltip. `::tooltip[tip]{anchor text}` |

### Layout Widgets

| Widget | Description |
|---|---|
| **Columns** | A responsive multi-column layout. `::columns[ratio]{col0\|\|col1\|\|...}` |
| **Grid** | A CSS grid container. Uses triple-colon. `:::grid[cols\|gap]{cell0\|\|cell1\|\|...}` |
| **Flex** | A CSS flex container. Uses triple-colon. `:::flex[gap\|align-items\|justify-content\|flex-wrap]{item0\|\|item1}` |
| **Hero** | A full-width hero section with configurable background and alignment. Uses triple-colon. `:::hero[bg\|align\|min-height]{body}` |
| **Section** | A full-width content section with optional title and subtitle. Uses triple-colon. `:::section[title\|subtitle\|align]{body}` |
| **Box** | A styled container box with configurable variant. Uses triple-colon. `:::box[variant]{body}` |
| **Div** | A generic `<div>` wrapper with custom class, id, or style. Uses triple-colon. `:::div[class\|id\|style]{body}` |
| **Center / Right** | Align block content. `::center{content}` / `::right{content}` |
| **Spacer / Divider** | Add whitespace or a horizontal rule. `::spacer[size]` / `::divider[style]` (both bodyless) |

### Typography Widgets

| Widget | Description |
|---|---|
| **Highlight** | Highlighted / marked text with colour variants (`yellow`, `green`, `pink`, `blue`, `orange`, `purple`). `::hl[colour]{text}` |
| **Styled Bold** | Bold text with special rendering styles: `gradient`, `outline`, `shadow`, `neon`, `stamp`, `underline`, `mono`. `::b[style]{text}` |
| **Color** | Inline text with a custom colour. `::color[hex]{text}` |
| **Glow** | Glowing text with a custom glow colour. `::glow[colour]{text}` |
| **Keyboard Key** | Render keyboard shortcuts as styled `<kbd>` elements. `::kbd{key combo}` |
| **Math** | Render a LaTeX / KaTeX expression. `::math{LaTeX}` (KaTeX loaded automatically in `--build` output) |

### Navigation Widgets

| Widget | Description |
|---|---|
| **Sidebar** | A slide-in navigation sidebar with a floating toggle button. Uses triple-colon. `:::sidebar[Title\|side\|width]{nav segments}` |
| **Router** | A hash-based single-page router with auto-generated tab navigation. `::router[default_page]{page_id:Title::body\|\|...}` |
| **Footer** | A site footer with an optional multi-column layout and copyright bar. `::footer[copyright\|accent]{col0\|\|col1\|\|...}` |

### Media & Embed Widgets

| Widget | Description |
|---|---|
| **Icon** | An inline SVG icon from the built-in icon set (209 icons across brand, arrows, status, media, files, editing, social, coding, UI, communication, people, nature, and misc categories). `::icon[name\|size\|colour]{fallback}` |
| **Icon Card** | A card with a large icon, title, and description text. `::iconcard[icon\|title]{description}` |
| **Inline SVG** | Render raw, sanitised SVG directly in the document. Uses triple-colon. `:::svg{markup}` |
| **Embed** | Embed external content: `youtube`, `github`, `spotify`, `codepen`, `map`, `pdf`, `audio`, `image`, `site`. `::embed[type]{src}` |

### Form Widgets

| Widget | Description |
|---|---|
| **Input** | A styled form input field. Supports `text`, `email`, `password`, `number`, `url`, `tel`, `search`, `date`, `datetime-local`, `time`, `range`, `color`, `file`. `::input[type\|placeholder\|id\|default\|min\|max\|step]{label}` |
| **Checkbox** | A styled checkbox with a label. `::checkbox[id\|value\|checked]{label}` |
| **Select** | A styled dropdown select. Options as `Value:Label` pairs. `::select[id\|default\|label]{opt0\|opt1\|...}` |
| **Button** | A styled button / link with styles `primary`, `secondary`, `ghost`, `outline`, `danger`, `success`. `::button[style\|action]{label}` |
| **Button Group** | A group of buttons rendered inline. Uses triple-colon. `:::btngroup{btn0\|\|btn1\|\|...}` |

### Control Flow Widgets

> All control-flow widgets are client-side — the condition is evaluated in the browser using a sanitised JS expression, evaluated once at page load.

| Widget | Description |
|---|---|
| **If** | Show content when a JavaScript expression is truthy. `::if[condition]{body}` |
| **Else** | Show content when the same expression is falsy. Pair with a preceding `::if`. `::else[condition]{body}` |
| **If / Else (inline)** | Compact inline branch showing one of two segments based on a condition. `::ifelse[condition]{then\|\|else}` |

### CSS Widgets

| Widget | Description |
|---|---|
| **Scoped CSS Block** | Define raw CSS that applies to the current document scope. Uses triple-colon. `:::css{raw CSS}` |
| **CSS Playground** | A live split-editor showing CSS and HTML side-by-side with instant preview. Uses triple-colon. `:::cssplay{css\|\|html}` |
| **CSS Variable** | Define a CSS custom property (`--variable`) for the document scope. `::cssvar[--name]{value}` |
| **Inline Style** | Apply arbitrary inline CSS to a block of content. `::style[css-properties]{body}` |
| **CSS Class** | Apply one or more CSS class names to a block of content. `::class[names]{body}` |

### Data Visualisation

| Widget | Description |
|---|---|
| **Chart** | A Chart.js chart powered by a JSON payload. Types: `bar`, `line`, `pie`, `doughnut`, `radar`, `polarArea`. `::chart[type]{json}` (Chart.js loaded automatically in `--build` output) |
| **Graph** | A rich server-side data graph with built-in themes. `::graph[type\|title\|palette\|height]{json}` |
| **Graph Playground** | An interactive graph editor. Uses triple-colon. `:::graphplay{json}` |
| **Demo Sandbox** | A live, editable HTML/CSS sandbox rendered in a sandboxed iframe. Uses triple-colon. `:::demo{html}` |

### Build-time Widgets

| Widget | Description |
|---|---|
| **Include** | Read another `.vml`, `.md`, or `.txt` file from disk and inline its fully-rendered output. Path is relative to the current source file. Processed at compile time by `voxmark compiler --build`. Circular includes are detected and skipped; missing files emit an HTML comment instead of an error; nesting is supported up to 16 levels deep. In the live editor (`/api/render`), includes render as empty placeholders since there is no filesystem context. |

---

## Multi-file Projects

Combine `::include` with `::router` and `:::sidebar` to build multi-page sites from separate files:

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
  home:Home::  
  ||about:About:: 
  ||contact:Contact:: 
}

::footer[© 2025]{Built with **VoxMark**}
```

Build with:

```bash
voxmark compiler --build index.vml -o build/
```

---

## CLI Reference

```bash
voxmark compiler --build input -o build-dir
```

| Flag | Description |
|---|---|
| `--build` | Required. Compile to HTML + CSS + WASM + JS loader. |
| `input` | Source `.vml` / `.md` file or directory. |
| `-o`, `--output` | Output directory (default: `build/`). |
| `--title` | Override HTML title. |
| `--no-wasm` | Skip `.wasm` / `loader.js` output. |
| `--no-wat` | Skip debug `.wat` output. |

Additional commands:

```bash
voxmark server  [--port PORT] [--host HOST] [--open]
voxmark lint [input]
voxmark format [input] [-o output] [-i]
voxmark ast [input] [--json]
voxmark init [directory]
voxmark watch [input] -o build-dir [--port PORT]
voxmark version
```

**Global flags:** `--verbose` / `-v` · `--quiet` / `-q` · `--no-color`

---

## Quick Reference Table

| Widget | Syntax | Triple? | Bodyless? |
|---|---|:---:|:---:|
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
| Include | `` | — | ✓ |
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
| SVG | `:::svg{}` | ✓ | — |
| Tab | `::tab[A\|B]{body\|\|body}` | — | — |
| Timeline | `::timeline{Title::Desc\|\|…}` | — | — |
| Tooltip | `::tooltip[tip text]{anchor}` | — | — |
| Variable | `::var[name]{value}` | — | — |

## VoxMark Language View after compilation.

![Graph 1](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/VML-Graph.PNG)
![Graph 2](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/VML-Graph2.PNG)
![Embed](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/VML-embed2.PNG)
![Custom Style](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/Custom%20Style%20-%20VML.PNG)
![Chart](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/Chart%20-%20VML.PNG)
![Hero Section](https://github.com/DivyanshuSinha136/VoxMark-Language/blob/main/VML/Hero%20-%20VML.PNG)

---

## License

VoxMark Language (VML) — created and maintained by **Divyanshu Sinha** ([@DivyanshuSinha136](https://github.com/DivyanshuSinha136)) and license under MIT.

---

Try Now VoxMark Language (`VML`).
