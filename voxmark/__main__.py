"""
VoxMark CLI — entry point for `python -m voxmark` and the `voxmark` console script.
Author: Divyanshu Sinha

Commands
--------
  voxmark compiler --build [INPUT] -o BUILD_DIR
          Compile a .vml/.md source file (or all *.vml/*.md in a dir) to:
            build/index.html      – full standalone HTML page
            build/styles.css      – extracted + base stylesheet bundle
            build/loader.js       – JS loader for the WASM module
            build/module.wasm     – WebAssembly binary
            build/debug.wat       – human-readable WAT (pass --no-wat to skip)

  voxmark server BUILD_DIR [--port PORT] [--host HOST] [--open]
          Serve a build directory over HTTP (production: waitress; fallback: stdlib).

  voxmark lint [INPUT]
          Lex + parse source and report errors / unknown commands.

  voxmark format [INPUT] [-o OUTPUT]
          Re-format VML source (normalises whitespace around widgets).

  voxmark ast [INPUT] [--json]
          Print the parsed AST in tree or JSON form.

  voxmark init [DIR]
          Scaffold a new VoxMark project in DIR.

  voxmark watch [INPUT] -o BUILD_DIR [--port PORT]
          Watch INPUT for changes and rebuild + hot-reload automatically.

  voxmark version
          Print version information.

Global flags
------------
  --verbose / -v    Enable DEBUG logging
  --quiet / -q      Suppress all non-error output
  --no-color        Disable ANSI colour in terminal output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import shutil
import signal
import sys
import textwrap
import time
from typing import List, Optional

# ── Colour helpers ─────────────────────────────────────────────────────────────

_USE_COLOUR: bool = sys.stdout.isatty() and os.name != 'nt' or os.environ.get('FORCE_COLOR')

def _c(code: str, text: str) -> str:  # noqa: D401
    """Wrap *text* in ANSI escape *code* if colour is enabled."""
    if not _USE_COLOUR:
        return text
    return f'\033[{code}m{text}\033[0m'

def _bold(t: str)    -> str: return _c('1',    t)
def _green(t: str)   -> str: return _c('32',   t)
def _yellow(t: str)  -> str: return _c('33',   t)
def _red(t: str)     -> str: return _c('31',   t)
def _cyan(t: str)    -> str: return _c('36',   t)
def _dim(t: str)     -> str: return _c('2',    t)


# ── Logger setup ───────────────────────────────────────────────────────────────

logger = logging.getLogger('voxmark')

def _setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.INFO)
    fmt   = '%(levelname)s  %(message)s' if verbose else '%(message)s'
    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)
    logging.getLogger('waitress').setLevel(logging.WARNING)


# ── Version ────────────────────────────────────────────────────────────────────

_VERSION = '1.0.0'

def _read_version() -> str:
    """Try to read version from package metadata; fall back to constant."""
    try:
        from importlib.metadata import version
        return version('voxmark')
    except Exception:
        return _VERSION


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_input(raw: Optional[str], extensions: tuple = ('.vml', '.md', '.txt')) -> pathlib.Path:
    """
    Resolve a user-supplied input path.  If *raw* is None or '-', read from
    stdin and write to a temp file, returning its path.
    """
    if raw is None or raw == '-':
        data = sys.stdin.read()
        tmp  = pathlib.Path(os.environ.get('TEMP', '/tmp')) / '_voxmark_stdin.vml'
        tmp.write_text(data, encoding='utf-8')
        return tmp

    p = pathlib.Path(raw)
    if not p.exists():
        _die(f'Input not found: {p}')
    return p


def _collect_sources(input_path: pathlib.Path) -> List[pathlib.Path]:
    """Return a list of VML/MD source files from a file or directory."""
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        sources = sorted(
            f for ext in ('*.vml', '*.md', '*.txt')
            for f in input_path.glob(ext)
        )
        if not sources:
            _die(f'No .vml / .md / .txt files found in {input_path}')
        return sources
    _die(f'Input is neither a file nor directory: {input_path}')


def _load_base_css() -> str:
    """
    Load the bundled VoxMark stylesheet.

    Search order:
      1. $VOXMARK_CSS env var
      2. <package_root>/style.css
      3. ./style.css  (CWD fallback)
    """
    env_css = os.environ.get('VOXMARK_CSS')
    if env_css:
        p = pathlib.Path(env_css)
        if p.exists():
            return p.read_text(encoding='utf-8')
        logger.warning('VOXMARK_CSS points to missing file: %s', env_css)

    # Alongside this file (installed as package)
    here = pathlib.Path(__file__).parent
    pkg_css = here / 'style.css'
    if pkg_css.exists():
        return pkg_css.read_text(encoding='utf-8')

    # CWD fallback (development / standalone use)
    cwd_css = pathlib.Path('style.css')
    if cwd_css.exists():
        logger.debug('Using style.css from cwd: %s', cwd_css.resolve())
        return cwd_css.read_text(encoding='utf-8')

    logger.warning('style.css not found; HTML output will have no base styles.')
    return ''


def _die(msg: str, code: int = 1) -> None:
    print(_red(f'error: {msg}'), file=sys.stderr)
    sys.exit(code)


def _ok(msg: str) -> None:
    print(_green('✓') + '  ' + msg)


def _info(msg: str) -> None:
    print(_cyan('→') + '  ' + msg)


def _warn(msg: str) -> None:
    print(_yellow('⚠') + '  ' + msg, file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════════
# Command: compiler --build
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_build(args: argparse.Namespace) -> int:
    """
    Compile VML source(s) to HTML + CSS + WASM + JS loader.

    Output layout inside BUILD_DIR:
      index.html       – standalone HTML page (or <stem>.html for multi-file)
      styles.css       – merged base + extracted stylesheet
      loader.js        – WASM loader (loadVoxMarkWASM)
      module.wasm      – WebAssembly binary
      debug.wat        – WAT text (omitted with --no-wat)
    """
    from .compiler import compile_vml   # lazy import — keeps CLI startup fast

    input_path = _resolve_input(getattr(args, 'input', None))
    sources    = _collect_sources(input_path)
    out_dir    = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_css   = _load_base_css()
    no_wasm    = getattr(args, 'no_wasm', False)
    no_wat     = getattr(args, 'no_wat',  False)
    title      = getattr(args, 'title',   None)

    t_start    = time.perf_counter()
    built      = 0

    for src in sources:
        _info(f'Compiling {src.name} …')
        source_text = src.read_text(encoding='utf-8')

        try:
            from .compiler import compile_vml_file
            result = compile_vml_file(src, base_css=base_css)
        except Exception as exc:
            _warn(f'{src.name}: compilation failed — {exc}')
            logger.debug('Traceback:', exc_info=True)
            continue

        stem      = src.stem if len(sources) > 1 else 'index'
        doc_title = title or stem.replace('_', ' ').replace('-', ' ').title()

        # ── HTML ─────────────────────────────────────────────────────────────
        css_bundle        = result.css.bundle(base_css)
        result.html.title = doc_title
        html_content       = result.html.to_page(css_href='styles.css', inline_css=False)
        html_out          = out_dir / f'{stem}.html'
        html_out.write_text(html_content, encoding='utf-8')
        _ok(f'{html_out.relative_to(out_dir.parent)}')

        # ── CSS ───────────────────────────────────────────────────────────────
        css_out = out_dir / 'styles.css'
        css_out.write_text(css_bundle, encoding='utf-8')
        _ok(f'{css_out.relative_to(out_dir.parent)}  ({len(css_bundle):,} bytes)')

        if not no_wasm:
            # ── WASM ─────────────────────────────────────────────────────────
            wasm_out = out_dir / 'module.wasm'
            wasm_out.write_bytes(result.wasm.wasm_bytes)
            _ok(f'{wasm_out.relative_to(out_dir.parent)}  ({len(result.wasm.wasm_bytes):,} bytes, '
                f'{result.wasm.widget_count} widgets)')

            # ── JS Loader ─────────────────────────────────────────────────────
            js_out = out_dir / 'loader.js'
            js_out.write_text(result.wasm.js_loader, encoding='utf-8')
            _ok(f'{js_out.relative_to(out_dir.parent)}')

            # ── WAT ───────────────────────────────────────────────────────────
            if not no_wat:
                wat_out = out_dir / 'debug.wat'
                wat_out.write_text(result.wasm.wat_text, encoding='utf-8')
                _ok(f'{wat_out.relative_to(out_dir.parent)}  (debug)')

        built += 1

    elapsed = time.perf_counter() - t_start
    if built:
        print()
        print(_bold(f'Build complete') + _dim(f'  {built} file(s)  {elapsed*1000:.0f} ms'))
        print(_dim(f'Output → {out_dir.resolve()}'))
    else:
        _die('No files were compiled successfully.')

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Command: server
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_server(args: argparse.Namespace) -> int:
    """Serve a build directory over HTTP."""
    build_dir = pathlib.Path(args.directory).resolve()   # must be absolute on Windows
    if not build_dir.is_dir():
        _die(f'Directory not found: {build_dir}')

    host  = getattr(args, 'host',  '127.0.0.1')
    port  = getattr(args, 'port',  8080)
    open_ = getattr(args, 'open',  False)
    url   = f'http://{host}:{port}/'

    print(_bold('VoxMark Dev Server'))
    print(_dim(f'Serving: {build_dir}'))
    print(_cyan(f'URL:     {url}'))
    print(_dim('Press Ctrl+C to stop.\n'))

    # Try waitress + Flask first (production WSGI server)
    try:
        from waitress import serve as _waitress_serve
        from flask import Flask, send_from_directory, redirect

        # Do NOT set static_folder — we manage all routes manually so that
        # Flask's built-in /static route doesn't compete with ours.
        _app = Flask(__name__, static_folder=None)
        _build_dir = build_dir  # capture for closures

        @_app.route('/')
        def _index():
            # send_from_directory requires an absolute directory on Windows
            return send_from_directory(str(_build_dir), 'index.html')

        @_app.route('/<path:filename>')
        def _static(filename: str):
            return send_from_directory(str(_build_dir), filename)

        @_app.errorhandler(404)
        def _not_found(e):
            idx = _build_dir / 'index.html'
            if idx.exists():
                return send_from_directory(str(_build_dir), 'index.html'), 200
            return f'<h1>404 — {e}</h1>', 404

        # Open browser after a short delay so the server is actually up
        if open_:
            import threading, webbrowser
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()

        _waitress_serve(_app, host=host, port=port, threads=4)

    except ImportError:
        # Fallback: Python stdlib http.server (no Flask/waitress required)
        import http.server
        import functools

        handler_cls = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(build_dir),
        )

        # Silence request logs when --quiet
        if logger.level >= logging.ERROR:
            class _QuietHandler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *a): pass
                def __init__(self, *a, **kw):
                    super().__init__(*a, directory=str(build_dir), **kw)
            handler_cls = _QuietHandler

        if open_:
            import threading, webbrowser
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()

        with http.server.TCPServer((host, port), handler_cls) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print('\nServer stopped.')

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Command: lint
# ══════════════════════════════════════════════════════════════════════════════

_KNOWN_CMDS = frozenset({
    'card', 'tab', 'alert', 'badge', 'progress', 'columns', 'callout',
    'kbd', 'tooltip', 'timeline', 'math', 'chart', 'embed', 'var', 'if',
    'color', 'glow', 'fold', 'demo', 'button', 'btngroup', 'hl', 'b',
    'icon', 'iconcard', 'svg', 'css', 'style', 'class', 'cssvar', 'cssplay',
    'div', 'box', 'hero', 'grid', 'flex', 'section', 'divider', 'spacer',
    'center', 'right', 'graph', 'graphplay',
})


def _cmd_lint(args: argparse.Namespace) -> int:
    """Lex + parse source and report any issues."""
    from .lexer  import Lexer, LexError
    from .parser import Parser, ParseError, Document, Widget

    input_path = _resolve_input(getattr(args, 'input', None))
    sources    = _collect_sources(input_path)
    total_errs = 0

    for src in sources:
        source_text = src.read_text(encoding='utf-8')
        errors: List[str] = []
        warnings: List[str] = []

        # Lex
        try:
            tokens = Lexer(source_text).tokenise()
        except LexError as exc:
            errors.append(f'Lex error: {exc}')
            tokens = []

        # Parse
        doc: Optional[Document] = None
        if tokens:
            try:
                doc = Parser(tokens).parse()
            except ParseError as exc:
                errors.append(f'Parse error: {exc}')

        # Walk AST for unknown commands
        if doc:
            def _walk(nodes):
                for n in nodes:
                    if isinstance(n, Widget):
                        if n.cmd and n.cmd not in _KNOWN_CMDS:
                            warnings.append(
                                f'L{n.line}: unknown command ::{n.cmd}'
                            )
                        for seg in n.segments:
                            _walk(seg.children)
            _walk(doc.children)

        # Report
        label = str(src) if len(sources) > 1 else src.name
        if errors or warnings:
            print(_bold(label))
            for e in errors:
                print('  ' + _red('✗') + f'  {e}')
                total_errs += 1
            for w in warnings:
                print('  ' + _yellow('⚠') + f'  {w}')
        else:
            print(_green('✓') + f'  {label}')

    if total_errs:
        print(_red(f'\n{total_errs} error(s) found.'))
        return 1

    print(_green('\nNo errors found.'))
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Command: format
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_format(args: argparse.Namespace) -> int:
    """
    Re-format VML source: normalise blank lines around widgets,
    strip trailing whitespace, ensure single trailing newline.
    """
    input_path = _resolve_input(getattr(args, 'input', None))
    out_path   = pathlib.Path(args.output) if getattr(args, 'output', None) else None

    text      = input_path.read_text(encoding='utf-8')
    formatted = _format_vml(text)

    if out_path:
        out_path.write_text(formatted, encoding='utf-8')
        _ok(f'Formatted → {out_path}')
    elif getattr(args, 'in_place', False):
        input_path.write_text(formatted, encoding='utf-8')
        _ok(f'Formatted in place: {input_path}')
    else:
        sys.stdout.write(formatted)

    return 0


def _format_vml(source: str) -> str:
    """
    Lightweight formatter:
      - Strip trailing whitespace from each line
      - Ensure blank line before :: / ::: widget lines
      - Collapse 3+ consecutive blank lines to 2
      - End with exactly one newline
    """
    lines    = source.splitlines()
    out: List[str] = []
    prev_blank = False

    for raw_line in lines:
        line = raw_line.rstrip()
        is_widget = line.lstrip().startswith('::')
        is_blank  = line == ''

        # Ensure blank line before a widget if the previous wasn't blank
        if is_widget and out and not prev_blank:
            out.append('')

        # Collapse excess blank lines
        if is_blank and prev_blank and out and out[-1] == '':
            continue

        out.append(line)
        prev_blank = is_blank

    # Trim trailing blank lines, add single final newline
    while out and out[-1] == '':
        out.pop()
    return '\n'.join(out) + '\n'


# ══════════════════════════════════════════════════════════════════════════════
# Command: ast
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_ast(args: argparse.Namespace) -> int:
    """Print the parsed AST."""
    from .parser import parse, Document, Widget, TextNode, VarRef

    input_path = _resolve_input(getattr(args, 'input', None))
    source     = input_path.read_text(encoding='utf-8')
    doc        = parse(source)

    if getattr(args, 'json', False):
        def _serialise(node) -> dict:
            if isinstance(node, TextNode):
                return {'type': 'text', 'value': node.text[:120], 'line': node.line}
            if isinstance(node, VarRef):
                return {'type': 'varref', 'name': node.name, 'line': node.line}
            if isinstance(node, Widget):
                return {
                    'type':     ':::' + node.cmd if node.triple else '::' + node.cmd,
                    'args':     node.args,
                    'segments': [[_serialise(c) for c in s.children] for s in node.segments],
                    'line':     node.line,
                }
            return {'type': 'unknown'}

        output = {'nodes': [_serialise(n) for n in doc.children]}
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write('\n')
    else:
        def _print(node, indent: int = 0) -> None:
            pad = '  ' * indent
            if isinstance(node, TextNode):
                preview = node.text[:60].replace('\n', '↵')
                print(f'{pad}{_dim("TEXT")}  {preview!r}')
            elif isinstance(node, VarRef):
                print(f'{pad}{_cyan("@" + node.name)}')
            elif isinstance(node, Widget):
                prefix = _bold(':::' if node.triple else '::')
                print(f'{pad}{prefix}{_green(node.cmd)}  {node.args!r}  '
                      f'{_dim(f"({len(node.segments)} seg)")}  L{node.line}')
                for seg in node.segments:
                    for child in seg.children:
                        _print(child, indent + 1)

        print(_bold(f'AST — {len(doc.children)} top-level nodes'))
        for child in doc.children:
            _print(child)

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Command: init
# ══════════════════════════════════════════════════════════════════════════════

_SAMPLE_VML = textwrap.dedent('''\
    # My VoxMark Document

    Welcome to **VoxMark**!

    ::alert[info]{This is an info alert. Edit me in `index.vml`.}

    ::card[Getting Started]{
    1. Edit `index.vml`
    2. Run `voxmark compiler --build index.vml -o build/`
    3. Run `voxmark server build/`
    }

    ::divider[]

    ::badge[VoxMark|#6c63ff] ::badge[v2.0|#22c55e]
''')

_GITIGNORE = 'build/\n__pycache__/\n*.pyc\n'

_README = textwrap.dedent('''\
    # VoxMark Project

    ## Build
    ```sh
    voxmark compiler --build index.vml -o build/
    ```

    ## Serve
    ```sh
    voxmark server build/
    ```

    ## Watch & rebuild
    ```sh
    voxmark watch index.vml -o build/ --port 8080
    ```
''')


def _cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new VoxMark project."""
    target = pathlib.Path(getattr(args, 'directory', None) or '.')
    target.mkdir(parents=True, exist_ok=True)

    files = {
        'index.vml':   _SAMPLE_VML,
        '.gitignore':  _GITIGNORE,
        'README.md':   _README,
    }

    for name, content in files.items():
        p = target / name
        if p.exists() and not getattr(args, 'force', False):
            _warn(f'Skipping existing file: {p}  (use --force to overwrite)')
        else:
            p.write_text(content, encoding='utf-8')
            _ok(f'Created {p}')

    build_dir = target / 'build'
    build_dir.mkdir(exist_ok=True)
    (build_dir / '.gitkeep').touch()
    _ok(f'Created {build_dir}/')

    print()
    print(_bold('Project ready.  Next steps:'))
    print(f'  cd {target}')
    print(f'  voxmark compiler --build index.vml -o build/')
    print(f'  voxmark server build/')
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Command: watch
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_watch(args: argparse.Namespace) -> int:
    """Watch source for changes and rebuild automatically."""
    input_path = _resolve_input(getattr(args, 'input', None))
    out_dir    = pathlib.Path(args.output)
    port       = getattr(args, 'port', 0)

    _info(f'Watching {input_path} → {out_dir}')
    if port:
        _info(f'Use `voxmark server {out_dir} --port {port}` in another terminal to serve.')
    print(_dim('Press Ctrl+C to stop.\n'))

    # Initial build
    _rebuild_once(input_path, out_dir)
    last_mtime = _mtime(input_path)

    def _sigint(sig, frame):
        print('\nWatch stopped.')
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    while True:
        time.sleep(0.5)
        mt = _mtime(input_path)
        if mt != last_mtime:
            last_mtime = mt
            print(_dim(f'\n[{time.strftime("%H:%M:%S")}] Change detected, rebuilding…'))
            _rebuild_once(input_path, out_dir)


def _mtime(p: pathlib.Path) -> float:
    try:
        return p.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _rebuild_once(src: pathlib.Path, out_dir: pathlib.Path) -> None:
    """Single build cycle used by the watch command."""
    from .compiler import compile_vml_file
    base_css = _load_base_css()
    try:
        result = compile_vml_file(src, base_css=base_css)
    except Exception as exc:
        _warn(f'Build failed: {exc}')
        logger.debug('', exc_info=True)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    css_bundle = result.css.bundle(base_css)
    (out_dir / 'index.html').write_text(
        result.html.to_page(css_href='styles.css', inline_css=False),
        encoding='utf-8',
    )
    (out_dir / 'styles.css').write_text(css_bundle, encoding='utf-8')
    (out_dir / 'module.wasm').write_bytes(result.wasm.wasm_bytes)
    (out_dir / 'loader.js').write_text(result.wasm.js_loader, encoding='utf-8')
    _ok(f'Rebuilt  →  {out_dir.resolve()}')


# ══════════════════════════════════════════════════════════════════════════════
# Command: version
# ══════════════════════════════════════════════════════════════════════════════

def _cmd_version(args: argparse.Namespace) -> int:
    ver = _read_version()
    print(f'VoxMark {_bold(ver)}  (Python {sys.version.split()[0]})')
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# Argument parser
# ══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog='voxmark',
        description='VoxMark — VML document compiler and dev server.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''\
            Examples:
              voxmark compiler --build index.vml -o build/
              voxmark server build/ --port 3000 --open
              voxmark lint src/
              voxmark format index.vml -o index_fmt.vml
              voxmark ast index.vml --json
              voxmark init my-project/
              voxmark watch index.vml -o build/ --port 8080
              voxmark version
        '''),
    )

    # Global flags
    root.add_argument('--verbose', '-v', action='store_true', help='Enable DEBUG logging')
    root.add_argument('--quiet',   '-q', action='store_true', help='Suppress non-error output')
    root.add_argument('--no-color',      action='store_true', help='Disable ANSI colour output')

    sub = root.add_subparsers(dest='command', metavar='COMMAND')
    sub.required = True

    # ── compiler --build ─────────────────────────────────────────────────────
    p_compiler = sub.add_parser('compiler', help='Compile VML source to build artefacts')
    p_compiler.add_argument('--build',   action='store_true', required=True,
                            help='Generate HTML, CSS, WASM, and JS loader')
    p_compiler.add_argument('input',     nargs='?', default=None,
                            metavar='INPUT',
                            help='Source .vml/.md file or directory (default: stdin)')
    p_compiler.add_argument('-o', '--output', default='build',
                            metavar='BUILD_DIR',
                            help='Output directory (default: build/)')
    p_compiler.add_argument('--title',   default=None,
                            help='HTML <title> for the output page')
    p_compiler.add_argument('--no-wasm', action='store_true',
                            help='Skip WASM / JS loader output')
    p_compiler.add_argument('--no-wat',  action='store_true',
                            help='Skip debug.wat output')
    p_compiler.set_defaults(func=_cmd_build)

    # ── server ────────────────────────────────────────────────────────────────
    p_server = sub.add_parser('server', help='Serve a build directory over HTTP')
    p_server.add_argument('directory', nargs='?', default='build',
                          help='Build directory to serve (default: build/)')
    p_server.add_argument('--host', default='127.0.0.1', help='Bind host (default: 127.0.0.1)')
    p_server.add_argument('--port', '-p', type=int, default=8080,
                          help='Port to listen on (default: 8080)')
    p_server.add_argument('--open', action='store_true',
                          help='Open browser automatically')
    p_server.set_defaults(func=_cmd_server)

    # ── lint ──────────────────────────────────────────────────────────────────
    p_lint = sub.add_parser('lint', help='Check VML source for errors')
    p_lint.add_argument('input', nargs='?', default=None,
                        metavar='INPUT',
                        help='Source file or directory (default: stdin)')
    p_lint.set_defaults(func=_cmd_lint)

    # ── format ───────────────────────────────────────────────────────────────
    p_fmt = sub.add_parser('format', help='Re-format VML source')
    p_fmt.add_argument('input', nargs='?', default=None,
                       metavar='INPUT',
                       help='Source file or directory (default: stdin)')
    p_fmt.add_argument('-o', '--output', default=None,
                       help='Output file (default: stdout)')
    p_fmt.add_argument('-i', '--in-place', action='store_true',
                       help='Edit file in place')
    p_fmt.set_defaults(func=_cmd_format)

    # ── ast ───────────────────────────────────────────────────────────────────
    p_ast = sub.add_parser('ast', help='Print parsed AST')
    p_ast.add_argument('input', nargs='?', default=None,
                       metavar='INPUT',
                       help='Source file (default: stdin)')
    p_ast.add_argument('--json', action='store_true',
                       help='Output as JSON instead of tree')
    p_ast.set_defaults(func=_cmd_ast)

    # ── init ──────────────────────────────────────────────────────────────────
    p_init = sub.add_parser('init', help='Scaffold a new VoxMark project')
    p_init.add_argument('directory', nargs='?', default='.',
                        help='Target directory (default: current directory)')
    p_init.add_argument('--force', action='store_true',
                        help='Overwrite existing files')
    p_init.set_defaults(func=_cmd_init)

    # ── watch ─────────────────────────────────────────────────────────────────
    p_watch = sub.add_parser('watch', help='Watch source and rebuild on changes')
    p_watch.add_argument('input', nargs='?', default=None,
                         metavar='INPUT',
                         help='Source file to watch (default: stdin)')
    p_watch.add_argument('-o', '--output', default='build',
                         metavar='BUILD_DIR',
                         help='Output directory (default: build/)')
    p_watch.add_argument('--port', '-p', type=int, default=0,
                         help='Print reminder to serve on this port')
    p_watch.set_defaults(func=_cmd_watch)

    # ── version ───────────────────────────────────────────────────────────────
    p_ver = sub.add_parser('version', help='Print version information')
    p_ver.set_defaults(func=_cmd_version)

    return root


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args   = parser.parse_args(argv)

    # Apply global flags
    global _USE_COLOUR
    if getattr(args, 'no_color', False):
        _USE_COLOUR = False

    _setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False),
    )

    func = getattr(args, 'func', None)
    if func is None:
        parser.print_help()
        return 1

    try:
        return func(args) or 0
    except KeyboardInterrupt:
        print('\nAborted.', file=sys.stderr)
        return 130
    except SystemExit:
        raise
    except Exception as exc:
        _die(str(exc))
        return 1   # unreachable; satisfies type checkers


if __name__ == '__main__':
    sys.exit(main())