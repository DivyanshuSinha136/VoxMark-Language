"""
VoxMark Parser — recursive-descent AST builder.
Author: Divyanshu Sinha

No regex.  Consumes a Token list from the Lexer and produces an AST whose
nodes map 1-to-1 onto VML constructs.

AST Node types
--------------
Document      – root, list of child nodes
TextNode      – raw text / markdown fragment
VarRef        – @name reference
Widget        – a ::cmd or :::cmd with optional arg-parts and body-parts
BodySegment   – one || segment inside a widget body (itself a sub-document)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .lexer import Lexer, Token, TK

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# AST Node Definitions
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TextNode:
    text: str
    line: int = 0

    def __repr__(self) -> str:
        return f'Text({self.text[:30]!r})'


@dataclass
class VarRef:
    name: str
    line: int = 0

    def __repr__(self) -> str:
        return f'VarRef({self.name!r})'


@dataclass
class BodySegment:
    """One || segment of a widget body."""
    children: List['ASTNode'] = field(default_factory=list)

    def text(self) -> str:
        """Reconstruct raw text of this segment (used by downstream compilers)."""
        parts: List[str] = []
        for child in self.children:
            if isinstance(child, TextNode):
                parts.append(child.text)
            elif isinstance(child, VarRef):
                parts.append('@' + child.name)
            elif isinstance(child, Widget):
                parts.append(child.raw)
        return ''.join(parts)


@dataclass
class Widget:
    """
    A VML widget node.

    triple   – True for :::cmd, False for ::cmd
    cmd      – command name (lowercase, normalised)
    args     – list of arg strings (split on |, stripped)
    segments – list of BodySegment (split on ||); empty for bodyless widgets
    raw      – original source text (preserved for WASM string table)
    line     – source line where the widget starts
    """
    triple:   bool
    cmd:      str
    args:     List[str]         = field(default_factory=list)
    segments: List[BodySegment] = field(default_factory=list)
    raw:      str               = ''
    line:     int               = 0

    # ── Convenience accessors ─────────────────────────────────────────────────

    @property
    def arg0(self) -> str:
        return self.args[0] if self.args else ''

    @property
    def arg1(self) -> str:
        return self.args[1] if len(self.args) > 1 else ''

    @property
    def arg2(self) -> str:
        return self.args[2] if len(self.args) > 2 else ''

    @property
    def body_text(self) -> str:
        """First segment raw text (most widgets have exactly one segment)."""
        return self.segments[0].text() if self.segments else ''

    @property
    def all_segments_text(self) -> List[str]:
        return [s.text() for s in self.segments]

    def __repr__(self) -> str:
        prefix = ':::' if self.triple else '::'
        return f'Widget({prefix}{self.cmd}, args={self.args!r}, segs={len(self.segments)})'


ASTNode = TextNode | VarRef | Widget


@dataclass
class Document:
    children: List[ASTNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f'Document({len(self.children)} nodes)'


# ══════════════════════════════════════════════════════════════════════════════
# Parser
# ══════════════════════════════════════════════════════════════════════════════

class ParseError(Exception):
    """Raised when the parser encounters an unexpected token sequence."""


class Parser:
    """
    Recursive-descent parser.  No regex anywhere.

    Grammar (simplified):
        document     ::= node*
        node         ::= widget | var_ref | text
        widget       ::= (COLON2 | COLON3) IDENT arg_list? body?
        arg_list     ::= LBRACKET arg_part (PIPE arg_part)* RBRACKET
        arg_part     ::= ARG_TEXT*
        body         ::= LBRACE body_segment (PIPE body_segment)* RBRACE
        body_segment ::= (BODY_TEXT | widget | var_ref)*
        var_ref      ::= AT VAR_NAME
        text         ::= TEXT+
    """

    __slots__ = ('_tokens', '_pos')

    def __init__(self, tokens: List[Token]) -> None:
        if not tokens:
            raise ValueError('Parser: token list must not be empty')
        self._tokens = tokens
        self._pos    = 0

    # ── Public ────────────────────────────────────────────────────────────────

    def parse(self) -> Document:
        """Parse the token stream and return the root Document."""
        doc = Document()
        while not self._at(TK.EOF):
            node = self._parse_node()
            if node is not None:
                doc.children.append(node)
        return doc

    # ── Token helpers ─────────────────────────────────────────────────────────

    def _cur(self) -> Token:
        return self._tokens[self._pos]

    def _at(self, kind: TK) -> bool:
        return self._cur().kind == kind

    def _eat(self, kind: TK) -> Token:
        tok = self._cur()
        if tok.kind != kind:
            raise ParseError(
                f'Expected {kind.name} but got {tok.kind.name} '
                f'({tok.value!r}) at L{tok.line}:{tok.col}'
            )
        self._pos += 1
        return tok

    def _advance(self) -> Token:
        tok = self._cur()
        self._pos += 1
        return tok

    # ── Node parsers ──────────────────────────────────────────────────────────

    def _parse_node(self) -> Optional[ASTNode]:
        cur = self._cur()

        if cur.kind == TK.TEXT:
            return self._parse_text()
        if cur.kind == TK.AT:
            return self._parse_var_ref()
        if cur.kind in (TK.COLON2, TK.COLON3):
            return self._parse_widget()

        # Orphaned / unexpected token at top level — treat as literal text
        self._advance()
        return TextNode(cur.value, cur.line) if cur.value else None

    def _parse_text(self) -> TextNode:
        """Merge consecutive TEXT tokens into a single node."""
        parts: List[str] = []
        line = self._cur().line
        while self._at(TK.TEXT):
            parts.append(self._advance().value)
        return TextNode(''.join(parts), line)

    def _parse_var_ref(self) -> VarRef:
        line = self._cur().line
        self._eat(TK.AT)
        name = ''
        if self._at(TK.VAR_NAME):
            name = self._advance().value
        return VarRef(name, line)

    def _parse_widget(self) -> Widget:
        start_tok = self._cur()
        triple    = start_tok.kind == TK.COLON3
        raw_parts = [start_tok.value]

        self._advance()   # consume :: or :::

        if not self._at(TK.IDENT):
            # Bare colons with no identifier — recover as plain text
            logger.debug('Parser: bare colons at L%d, treating as text', start_tok.line)
            return Widget(triple, '', [], [], start_tok.value, start_tok.line)

        ident_tok = self._advance()
        cmd       = ident_tok.value.lower()
        raw_parts.append(ident_tok.value)

        # ── Arg list [arg | arg | …] ─────────────────────────────────────────
        args: List[str] = []
        if self._at(TK.LBRACKET):
            raw_parts.append('[')
            self._advance()   # consume [
            args, arg_raw = self._parse_args()
            raw_parts.extend(arg_raw)
            if self._at(TK.RBRACKET):
                raw_parts.append(']')
                self._advance()
            else:
                logger.warning('Parser: unclosed [ in %s widget at L%d', cmd, start_tok.line)

        # ── Body { … || … } ─────────────────────────────────────────────────
        segments: List[BodySegment] = []
        if self._at(TK.LBRACE):
            raw_parts.append('{')
            self._advance()   # consume {
            segments, body_raw = self._parse_body()
            raw_parts.extend(body_raw)
            if self._at(TK.RBRACE):
                raw_parts.append('}')
                self._advance()
            else:
                logger.warning('Parser: unclosed { in %s widget at L%d', cmd, start_tok.line)

        return Widget(triple, cmd, args, segments, ''.join(raw_parts), start_tok.line)

    def _parse_args(self) -> Tuple[List[str], List[str]]:
        """Parse ARG_TEXT (PIPE ARG_TEXT)*  →  (arg_strings, raw_parts)."""
        args: List[str] = []
        raw:  List[str] = []
        buf:  List[str] = []

        while not self._at(TK.RBRACKET) and not self._at(TK.EOF):
            tok = self._cur()
            if tok.kind == TK.ARG_TEXT:
                buf.append(tok.value)
                raw.append(tok.value)
                self._advance()
            elif tok.kind == TK.PIPE:
                args.append(''.join(buf).strip())
                buf = []
                raw.append('|')
                self._advance()
            else:
                # Unexpected token — absorb as text to be resilient
                buf.append(tok.value)
                raw.append(tok.value)
                self._advance()

        args.append(''.join(buf).strip())
        return args, raw

    def _parse_body(self) -> Tuple[List[BodySegment], List[str]]:
        """Parse body segments split by || tokens → (segments, raw_parts)."""
        segments: List[BodySegment] = []
        raw:      List[str]         = []
        current                     = BodySegment()

        while not self._at(TK.RBRACE) and not self._at(TK.EOF):
            tok = self._cur()

            if tok.kind == TK.PIPE and tok.value == '||':
                segments.append(current)
                current = BodySegment()
                raw.append('||')
                self._advance()

            elif tok.kind == TK.BODY_TEXT:
                # Body text may contain nested VML — re-lex and re-parse
                sub_nodes = self._parse_body_text(tok.value, tok.line)
                current.children.extend(sub_nodes)
                raw.append(tok.value)
                self._advance()

            elif tok.kind == TK.AT:
                vref = self._parse_var_ref()
                current.children.append(vref)
                raw.append('@' + vref.name)

            elif tok.kind in (TK.COLON2, TK.COLON3):
                w = self._parse_widget()
                current.children.append(w)
                raw.append(w.raw)

            else:
                # Any other orphaned token — treat as text
                current.children.append(TextNode(tok.value, tok.line))
                raw.append(tok.value)
                self._advance()

        segments.append(current)
        return segments, raw

    def _parse_body_text(self, text: str, line: int) -> List[ASTNode]:
        """
        Body text may itself contain @var refs or nested widgets.
        Re-lex and re-parse the text fragment; fall back to a plain TextNode
        when there is no VML inside.
        """
        try:
            sub_tokens = Lexer(text).tokenise()
        except Exception as exc:  # pragma: no cover
            logger.warning('Parser: sub-lex failed (%s); treating as plain text', exc)
            return [TextNode(text, line)]

        has_vml = any(t.kind in (TK.COLON2, TK.COLON3, TK.AT) for t in sub_tokens)
        if not has_vml:
            return [TextNode(text, line)]

        try:
            sub_doc = Parser(sub_tokens).parse()
            return sub_doc.children
        except ParseError as exc:
            logger.warning('Parser: sub-parse failed (%s); treating as plain text', exc)
            return [TextNode(text, line)]


# ── Convenience function ──────────────────────────────────────────────────────

def parse(source: str) -> Document:
    """Lex + parse a VML source string into a Document AST."""
    tokens = Lexer(source).tokenise()
    return Parser(tokens).parse()