"""
VoxMark Lexer — hand-written character-by-character tokeniser.
Author: Divyanshu Sinha

No regex.  Converts raw VML source text into a flat list of typed Token objects.

Token kinds
-----------
TEXT          – plain text (not a VML construct)
COLON2        – ::
COLON3        – :::
IDENT         – command name after :: / :::
LBRACKET      – [
RBRACKET      – ]
LBRACE        – {
RBRACE        – }
ARG_TEXT      – text inside [ … ]
BODY_TEXT     – raw text inside { … } (may span lines)
PIPE          – | inside ARG or BODY
AT            – @ (variable reference prefix)
VAR_NAME      – identifier after @
EOF           – end of stream
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import List

logger = logging.getLogger(__name__)

# ── Token kinds ───────────────────────────────────────────────────────────────

class TK(Enum):
    TEXT         = auto()
    COLON2       = auto()
    COLON3       = auto()
    IDENT        = auto()
    LBRACKET     = auto()
    RBRACKET     = auto()
    LBRACE       = auto()
    RBRACE       = auto()
    ARG_TEXT     = auto()
    BODY_TEXT    = auto()
    PIPE         = auto()
    AT           = auto()
    VAR_NAME     = auto()
    EOF          = auto()


# Commands that take NO body braces
_BODYLESS_CMDS: frozenset[str] = frozenset({'divider', 'spacer'})

# Commands that use triple colon (informational; lexer accepts both for any cmd)
_TRIPLE_CMDS: frozenset[str] = frozenset({
    'fold', 'demo', 'btngroup', 'svg', 'css', 'cssplay',
    'div', 'box', 'hero', 'grid', 'flex', 'section',
    'graphplay',
})

# Maximum nesting depth for brace bodies to prevent stack-overflow-style abuse
_MAX_BRACE_DEPTH = 32


# ── Token dataclass ───────────────────────────────────────────────────────────

@dataclass(slots=True)
class Token:
    kind:  TK
    value: str
    line:  int = 0
    col:   int = 0

    def __repr__(self) -> str:
        v = self.value[:30].replace('\n', '\\n')
        return f'Token({self.kind.name}, {v!r}, L{self.line}:{self.col})'


# ── Exceptions ────────────────────────────────────────────────────────────────

class LexError(Exception):
    """Raised when the lexer encounters unrecoverable input."""


# ══════════════════════════════════════════════════════════════════════════════
# Lexer
# ══════════════════════════════════════════════════════════════════════════════

class Lexer:
    """
    Single-pass VML lexer.  No regular expressions.

    The VML grammar has two syntactic modes:
      - TOP LEVEL: scan for :: / ::: openers, @ references, or plain text.
      - INSIDE WIDGET: after opening ::cmd[, tokenise arg chars until ].
                       After opening {, tokenise body chars tracking brace depth.
    """

    __slots__ = ('_src', '_pos', '_line', '_col', '_len', '_tokens')

    def __init__(self, source: str) -> None:
        if not isinstance(source, str):
            raise TypeError(f'Lexer expects str, got {type(source).__name__}')
        self._src    = source
        self._pos    = 0
        self._line   = 1
        self._col    = 1
        self._len    = len(source)
        self._tokens: List[Token] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def tokenise(self) -> List[Token]:
        """Run the lexer and return the complete token list."""
        self._tokens = []
        while self._pos < self._len:
            self._lex_top()
        self._emit(TK.EOF, '')
        return self._tokens

    # Alias for API consistency
    tokenize = tokenise

    # ── Character helpers ─────────────────────────────────────────────────────

    def _peek(self, offset: int = 0) -> str:
        p = self._pos + offset
        return self._src[p] if p < self._len else ''

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        if ch == '\n':
            self._line += 1
            self._col   = 1
        else:
            self._col  += 1
        return ch

    def _emit(self, kind: TK, value: str) -> None:
        self._tokens.append(Token(kind, value, self._line, self._col))

    # ── Top-level scanner ─────────────────────────────────────────────────────

    def _lex_top(self) -> None:
        ch = self._peek()

        # Check for ::: or ::
        if ch == ':' and self._peek(1) == ':':
            if self._peek(2) == ':':
                self._lex_triple_widget()
            else:
                self._lex_double_widget()
            return

        # @ variable reference
        if ch == '@':
            self._advance()       # consume @
            line, col = self._line, self._col
            self._emit(TK.AT, '@')
            name = self._read_ident()
            if name:
                self._emit(TK.VAR_NAME, name)
            return

        # Plain text — accumulate until next :: or @ or EOF
        self._lex_text()

    def _lex_text(self) -> None:
        start = self._pos
        while self._pos < self._len:
            ch = self._peek()
            if ch == ':' and self._peek(1) == ':':
                break
            if ch == '@':
                break
            self._advance()
        if self._pos > start:
            self._emit(TK.TEXT, self._src[start:self._pos])

    # ── Widget scanners ───────────────────────────────────────────────────────

    def _lex_double_widget(self) -> None:
        """Scan ::cmd[arg]{body} or ::cmd[arg] (bodyless)."""
        self._advance(); self._advance()          # consume ::
        self._emit(TK.COLON2, '::')

        cmd = self._read_ident()
        if not cmd:
            # Bare colons — not actually a widget; recover as text
            self._tokens.pop()
            self._emit(TK.TEXT, '::')
            return
        self._emit(TK.IDENT, cmd)

        self._lex_optional_arg()

        if cmd.lower() in _BODYLESS_CMDS:
            return

        if self._peek() == '{':
            self._lex_brace_body()

    def _lex_triple_widget(self) -> None:
        """Scan :::cmd[arg]{body}."""
        self._advance(); self._advance(); self._advance()  # consume :::
        self._emit(TK.COLON3, ':::')

        cmd = self._read_ident()
        if not cmd:
            self._tokens.pop()
            self._emit(TK.TEXT, ':::')
            return
        self._emit(TK.IDENT, cmd)

        self._lex_optional_arg()

        if self._peek() == '{':
            self._lex_brace_body()

    def _lex_optional_arg(self) -> None:
        """Scan [arg] if present.  Emits LBRACKET, ARG_TEXT (with PIPEs), RBRACKET."""
        if self._peek() != '[':
            return
        self._advance()                           # consume [
        self._emit(TK.LBRACKET, '[')
        self._lex_arg_content()
        if self._peek() == ']':
            self._advance()
            self._emit(TK.RBRACKET, ']')
        else:
            logger.debug('Lexer: unclosed [ starting at L%d', self._line)

    def _lex_arg_content(self) -> None:
        """Scan text inside [ … ], splitting on |."""
        buf: List[str] = []
        while self._pos < self._len:
            ch = self._peek()
            if ch == ']':
                break
            if ch == '|':
                self._emit(TK.ARG_TEXT, ''.join(buf))
                buf = []
                self._advance()
                self._emit(TK.PIPE, '|')
            else:
                buf.append(self._advance())
        if buf:
            self._emit(TK.ARG_TEXT, ''.join(buf))

    def _lex_brace_body(self) -> None:
        """
        Scan { … } body tracking brace depth.
        Emits LBRACE, BODY_TEXT (split on ||), RBRACE.
        Nested {} are preserved literally inside BODY_TEXT.
        """
        self._advance()                           # consume opening {
        self._emit(TK.LBRACE, '{')

        depth = 1
        buf: List[str] = []

        while self._pos < self._len and depth > 0:
            if depth > _MAX_BRACE_DEPTH:
                raise LexError(
                    f'Brace nesting exceeds {_MAX_BRACE_DEPTH} levels at '
                    f'L{self._line}:{self._col} — possible runaway input'
                )

            ch = self._peek()

            if ch == '{':
                depth += 1
                buf.append(self._advance())

            elif ch == '}':
                depth -= 1
                if depth == 0:
                    if buf:
                        self._emit_body_text(''.join(buf))
                    self._advance()               # consume }
                    self._emit(TK.RBRACE, '}')
                else:
                    buf.append(self._advance())

            elif ch == '|' and self._peek(1) == '|':
                # || segment separator
                if buf:
                    self._emit_body_text(''.join(buf))
                buf = []
                self._advance(); self._advance()  # consume ||
                self._emit(TK.PIPE, '||')

            else:
                buf.append(self._advance())

        if depth != 0:
            # Unclosed brace — emit whatever we have and warn
            if buf:
                self._emit_body_text(''.join(buf))
            logger.warning('Lexer: unclosed { at end of input (depth=%d)', depth)

    def _emit_body_text(self, text: str) -> None:
        self._emit(TK.BODY_TEXT, text)

    # ── Utility ───────────────────────────────────────────────────────────────

    def _read_ident(self) -> str:
        """Read [a-zA-Z_][a-zA-Z0-9_]* without regex."""
        if self._pos >= self._len:
            return ''
        ch = self._peek()
        if not (ch.isalpha() or ch == '_'):
            return ''
        buf: List[str] = []
        while self._pos < self._len:
            c = self._peek()
            if c.isalnum() or c == '_':
                buf.append(self._advance())
            else:
                break
        return ''.join(buf)