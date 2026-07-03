"""
VoxMark — Flask application factory.
Author: Divyanshu Sinha
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, Response

from .renderer import render, get_pygments_css
from .firewall import init_firewall, require_safe_content
from .compiler import compile_vml

logger = logging.getLogger('voxmark.app')


def create_app(debug: bool = False) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
    )
    app.config.update(
        SECRET_KEY=os.environ.get('VOXMARK_SECRET', os.urandom(32)),
        DEBUG=debug,
        MAX_CONTENT_LENGTH=512 * 1024,
        JSON_SORT_KEYS=False,
    )

    init_firewall(app)

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        from .examples import WELCOME_DOC
        initial_html = render(WELCOME_DOC)
        return render_template(
            'app.html',
            initial_source=WELCOME_DOC,
            initial_html=initial_html,
            pygments_css=get_pygments_css(),
        )

    @app.route('/api/render', methods=['POST'])
    @require_safe_content
    def api_render():
        data   = request.get_json(silent=True) or {}
        source = data.get('source', '')
        if not isinstance(source, str):
            return jsonify(error='source must be a string'), 400
        try:
            html_out = render(source)
            return jsonify(html=html_out)
        except Exception as exc:
            logger.exception('Render error')
            return jsonify(error=f'Render error: {exc}'), 500

    @app.route('/api/compile', methods=['POST'])
    @require_safe_content
    def api_compile():
        """
        Full compile: Lexer → Parser → AST → HTML + CSS + WASM.
        POST JSON: { "source": "...", "target": "all"|"html"|"css"|"wasm" }
        """
        data   = request.get_json(silent=True) or {}
        source = data.get('source', '')
        target = data.get('target', 'all').lower()
        if not isinstance(source, str):
            return jsonify(error='source must be a string'), 400
        try:
            result = compile_vml(source)
            resp = {
                'widget_count': result.wasm.widget_count,
                'source_len':   result.source_len,
                'ast_nodes':    len(result.ast.children),
            }
            if target in ('all', 'html'):
                resp['html'] = result.html.html
            if target in ('all', 'css'):
                resp['css'] = result.css.bundle()
                #resp['css'] = result.css
            if target in ('all', 'wasm'):
                resp['wasm_b64']    = result.wasm.wasm_b64()
                resp['wasm_bytes']  = len(result.wasm.wasm_bytes)
                resp['wat']         = result.wasm.wat_text
                resp['js_loader']   = result.wasm.js_loader
                resp['inline_html'] = result.wasm.inline_html()
                resp['wasm_page']   = result.wasm.standalone_page(title='VoxMark WASM Export')
            return jsonify(**resp)
        except Exception as exc:
            logger.exception('Compile error')
            return jsonify(error=f'Compile error: {exc}'), 500

    @app.route('/api/compile/wasm', methods=['POST'])
    @require_safe_content
    def api_compile_wasm_binary():
        """Download raw .wasm binary."""
        data   = request.get_json(silent=True) or {}
        source = data.get('source', '')
        try:
            result = compile_vml(source)
            return Response(
                result.wasm.wasm_bytes,
                mimetype='application/wasm',
                headers={'Content-Disposition': 'attachment; filename="voxmark.wasm"'},
            )
        except Exception as exc:
            return jsonify(error=str(exc)), 500

    @app.route('/api/examples')
    def api_examples():
        from .examples import EXAMPLES
        return jsonify(examples=[{'name': e['name'], 'key': e['key']} for e in EXAMPLES])

    @app.route('/api/examples/<key>')
    def api_example(key: str):
        from .examples import EXAMPLES
        for ex in EXAMPLES:
            if ex['key'] == key:
                return jsonify(source=ex['source'])
        return jsonify(error='Not found'), 404

    @app.route('/api/pygments.css')
    def pygments_css():
        return Response(get_pygments_css(), mimetype='text/css')

    @app.route('/health')
    def health():
        return jsonify(status='ok', version='1.0.0', engine='VoxMark',
                       compiler='Lexer+Parser+WASMEncoder')

    # ── Error handlers ────────────────────────────────────────────────────────

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error='Bad Request'), 400

    @app.errorhandler(413)
    def too_large(e):
        return jsonify(error='Payload too large (max 512 KB)'), 413

    @app.errorhandler(429)
    def too_many(e):
        return jsonify(error='Rate limit exceeded'), 429

    @app.errorhandler(500)
    def internal(e):
        return jsonify(error='Internal server error'), 500

    logger.info('VoxMark app created (debug=%s)', debug)
    return app
