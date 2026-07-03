"""
VoxMark — Markdown + VML Interactive Document Engine
Author: Divyanshu Sinha
Version: 1.0.0
"""

__version__ = '1.0.0'
__author__  = 'Divyanshu Sinha'
__email__   = 'divyanshu.sinha631@gmail.com'

from .app      import create_app
from .renderer import render
from .language import transform_vml
from .lexer    import Lexer, Token, TK
from .parser   import Parser, Document, Widget, TextNode, VarRef, parse
from .compiler import compile_vml, HTMLCompiler, CSSCompiler, WASMCompiler, CompileResult

__all__ = [
    'create_app', 'render', 'transform_vml',
    'Lexer', 'Token', 'TK',
    'Parser', 'Document', 'Widget', 'TextNode', 'VarRef', 'parse',
    'compile_vml', 'HTMLCompiler', 'CSSCompiler', 'WASMCompiler', 'CompileResult',
]
