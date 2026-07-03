"""
VoxMark WASM Binary Encoder — pure Python, zero external dependencies.
Author: Divyanshu Sinha

Implements the WebAssembly binary format (MVP + bulk-memory subset) directly.
Produces valid .wasm files that browsers can load natively.

Reference: https://webassembly.github.io/spec/core/binary/index.html

The WASM module we emit:
  - Stores each VML widget's rendered HTML as a data segment in linear memory
  - Exports a `get_widget(index: i32) -> (ptr: i32, len: i32)` function
  - Exports a `widget_count() -> i32` function
  - Exports the memory itself so JS can read the strings out
  - Provides a `render_all() -> i32` function returning total byte count
"""

from __future__ import annotations
import struct
from typing import List, Tuple


# ── LEB128 encoding (variable-length integer, used throughout WASM binary) ────

def _uleb128(n: int) -> bytes:
    """Unsigned LEB128."""
    assert n >= 0
    out = []
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            break
    return bytes(out)


def _sleb128(n: int) -> bytes:
    """Signed LEB128."""
    out = []
    more = True
    while more:
        b = n & 0x7F
        n >>= 7
        if (n == 0 and not (b & 0x40)) or (n == -1 and (b & 0x40)):
            more = False
        else:
            b |= 0x80
        out.append(b)
    return bytes(out)


def _vec(items: List[bytes]) -> bytes:
    """WASM vector: u32 count followed by concatenated items."""
    return _uleb128(len(items)) + b''.join(items)


def _str_bytes(s: str) -> bytes:
    """WASM name: length-prefixed UTF-8."""
    enc = s.encode('utf-8')
    return _uleb128(len(enc)) + enc


def _section(section_id: int, content: bytes) -> bytes:
    """Wrap content in a WASM section."""
    return bytes([section_id]) + _uleb128(len(content)) + content


# ── WASM type encodings ────────────────────────────────────────────────────────
I32   = b'\x7f'
VOID  = b'\x40'
FUNC  = b'\x60'


# ── Instruction opcodes ────────────────────────────────────────────────────────
OP_UNREACHABLE  = b'\x00'
OP_NOP          = b'\x01'
OP_BLOCK        = b'\x02'
OP_LOOP         = b'\x03'
OP_IF           = b'\x04'
OP_ELSE         = b'\x05'
OP_END          = b'\x0b'
OP_BR           = b'\x0c'
OP_BR_IF        = b'\x0d'
OP_RETURN       = b'\x0f'
OP_CALL         = b'\x10'
OP_DROP         = b'\x1a'
OP_SELECT       = b'\x1b'
OP_LOCAL_GET    = b'\x20'
OP_LOCAL_SET    = b'\x21'
OP_LOCAL_TEE    = b'\x22'
OP_GLOBAL_GET   = b'\x23'
OP_GLOBAL_SET   = b'\x24'
OP_I32_LOAD     = b'\x28'
OP_I32_STORE    = b'\x36'
OP_MEMORY_SIZE  = b'\x3f'
OP_MEMORY_GROW  = b'\x40'
OP_I32_CONST    = b'\x41'
OP_I32_EQZ     = b'\x45'
OP_I32_EQ      = b'\x46'
OP_I32_NE      = b'\x47'
OP_I32_LT_S    = b'\x48'
OP_I32_LT_U    = b'\x49'
OP_I32_GT_S    = b'\x4a'
OP_I32_GT_U    = b'\x4b'
OP_I32_LE_S    = b'\x4c'
OP_I32_GE_S    = b'\x4e'
OP_I32_ADD     = b'\x6a'
OP_I32_SUB     = b'\x6b'
OP_I32_MUL     = b'\x6c'
OP_I32_DIV_S   = b'\x6d'
OP_I32_REM_S   = b'\x6f'
OP_I32_AND     = b'\x71'
OP_I32_OR      = b'\x72'
OP_I32_SHL     = b'\x74'
OP_I32_SHR_S   = b'\x75'


def _i32_const(n: int) -> bytes:
    return OP_I32_CONST + _sleb128(n)


def _local_get(idx: int) -> bytes:
    return OP_LOCAL_GET + _uleb128(idx)


def _local_set(idx: int) -> bytes:
    return OP_LOCAL_SET + _uleb128(idx)


def _global_get(idx: int) -> bytes:
    return OP_GLOBAL_GET + _uleb128(idx)


def _global_set(idx: int) -> bytes:
    return OP_GLOBAL_SET + _uleb128(idx)


def _call(idx: int) -> bytes:
    return OP_CALL + _uleb128(idx)


def _br_if(depth: int) -> bytes:
    return OP_BR_IF + _uleb128(depth)


def _br(depth: int) -> bytes:
    return OP_BR + _uleb128(depth)


# ── WASMModule builder ─────────────────────────────────────────────────────────

class WASMModule:
    """
    Builds a complete WebAssembly module binary from VML widget data.

    Memory layout:
        [0  .. 4]   : i32 widget_count
        [4  .. 8*N+4] : widget table — for each widget: [ptr: i32, len: i32]
        [8*N+4 .. ] : UTF-8 HTML string data, packed sequentially

    Exported functions:
        widget_count() -> i32       : number of widgets
        get_widget_ptr(i: i32) -> i32 : pointer to widget i's HTML in memory
        get_widget_len(i: i32) -> i32 : byte length of widget i's HTML
        render_all()   -> i32       : total bytes of all HTML combined
    """

    MAGIC   = b'\x00asm'
    VERSION = b'\x01\x00\x00\x00'

    # Section IDs
    SEC_TYPE     = 1
    SEC_IMPORT   = 2
    SEC_FUNCTION = 3
    SEC_TABLE    = 4
    SEC_MEMORY   = 5
    SEC_GLOBAL   = 6
    SEC_EXPORT   = 7
    SEC_START    = 8
    SEC_ELEMENT  = 9
    SEC_CODE     = 10
    SEC_DATA     = 11

    def __init__(self, widgets: List[Tuple[str, str]]) -> None:
        """
        widgets: list of (widget_id, html_string) pairs.
        widget_id is a short identifier like 'card_0', 'alert_1' etc.
        """
        self.widgets   = widgets            # [(id, html), ...]
        self._strings: List[bytes] = []     # UTF-8 encoded HTML strings
        self._offsets: List[int]   = []     # byte offset of each string in data seg
        self._lengths: List[int]   = []     # byte length of each string

        self._layout_strings()

    def _layout_strings(self) -> None:
        """Compute offsets and lengths for all widget HTML strings."""
        # Header: 4 bytes for count + 8 bytes per widget (ptr, len)
        header_size = 4 + 8 * len(self.widgets)
        offset = header_size

        for wid, html_str in self.widgets:
            enc = html_str.encode('utf-8')
            self._strings.append(enc)
            self._offsets.append(offset)
            self._lengths.append(len(enc))
            offset += len(enc)

        self._total_data_size = offset

    def build(self) -> bytes:
        """
        Assemble the complete .wasm binary.

        Section order MUST follow the WebAssembly spec (ascending section IDs):
          1  Type      — function signatures
          3  Function  — maps function index → type index
          5  Memory    — linear memory declaration
          6  Global    — global variable declarations
          7  Export    — exported names (references function indices from sec 3)
          10 Code      — function bodies
          11 Data      — initialisation data segments
        """
        parts = [self.MAGIC, self.VERSION]
        parts.append(self._type_section())       # sec 1
        parts.append(self._function_section())   # sec 3  ← must come before Export
        parts.append(self._memory_section())     # sec 5
        parts.append(self._global_section())     # sec 6
        parts.append(self._export_section())     # sec 7  ← references func indices 0-3
        parts.append(self._code_section())       # sec 10
        parts.append(self._data_section())       # sec 11
        return b''.join(parts)

    # ── Section builders ───────────────────────────────────────────────────────

    def _type_section(self) -> bytes:
        """
        Type section: function signatures.
        Type 0: () -> i32          (widget_count, render_all)
        Type 1: (i32) -> i32       (get_widget_ptr, get_widget_len)
        """
        t0 = FUNC + _vec([]) + _vec([I32])          # () -> i32
        t1 = FUNC + _vec([I32]) + _vec([I32])        # (i32) -> i32
        return _section(self.SEC_TYPE, _vec([t0, t1]))

    def _memory_section(self) -> bytes:
        """One memory, min pages needed to hold all data (64KB per page)."""
        page_size  = 65536
        pages_needed = (self._total_data_size + page_size - 1) // page_size
        pages_needed = max(pages_needed, 1)
        # limit type 0 = no max limit
        mem = b'\x00' + _uleb128(pages_needed)
        return _section(self.SEC_MEMORY, _vec([mem]))

    def _global_section(self) -> bytes:
        """
        One mutable global: g0 = widget_count (i32).
        """
        count = len(self.widgets)
        # global type: i32, mutable
        gtype = I32 + b'\x01'
        # init expr: i32.const N, end
        init  = _i32_const(count) + OP_END
        g0    = gtype + init
        return _section(self.SEC_GLOBAL, _vec([g0]))

    def _function_section(self) -> bytes:
        """
        Function index → type index mapping.
        func 0: widget_count  → type 0   () -> i32
        func 1: get_widget_ptr → type 1  (i32) -> i32
        func 2: get_widget_len → type 1  (i32) -> i32
        func 3: render_all    → type 0   () -> i32
        """
        types = [
            _uleb128(0),  # widget_count  : () -> i32
            _uleb128(1),  # get_widget_ptr: (i32) -> i32
            _uleb128(1),  # get_widget_len: (i32) -> i32
            _uleb128(0),  # render_all    : () -> i32
        ]
        return _section(self.SEC_FUNCTION, _vec(types))

    def _export_section(self) -> bytes:
        """Export memory + 4 functions."""
        # export kind 0=function, 2=memory
        exports = [
            _str_bytes('memory')         + b'\x02' + _uleb128(0),
            _str_bytes('widget_count')   + b'\x00' + _uleb128(0),
            _str_bytes('get_widget_ptr') + b'\x00' + _uleb128(1),
            _str_bytes('get_widget_len') + b'\x00' + _uleb128(2),
            _str_bytes('render_all')     + b'\x00' + _uleb128(3),
        ]
        return _section(self.SEC_EXPORT, _vec(exports))

    def _code_section(self) -> bytes:
        """Function bodies for all 4 exported functions."""
        bodies = [
            self._fn_widget_count(),
            self._fn_get_widget_ptr(),
            self._fn_get_widget_len(),
            self._fn_render_all(),
        ]
        return _section(self.SEC_CODE, _vec(bodies))

    def _encode_body(self, locals_: List[bytes], instrs: bytes) -> bytes:
        """Encode a function body: locals vec + instructions + end."""
        loc_section = _vec(locals_)
        body = loc_section + instrs + OP_END
        return _uleb128(len(body)) + body

    # ── Function bodies ────────────────────────────────────────────────────────

    def _fn_widget_count(self) -> bytes:
        """
        widget_count() -> i32
        return global[0]   ;; = widget count stored in g0
        """
        instrs = _global_get(0) + OP_RETURN
        return self._encode_body([], instrs)

    def _fn_get_widget_ptr(self) -> bytes:
        """
        get_widget_ptr(i: i32) -> i32
        Memory layout: byte 0..3 = count, then pairs of (ptr: i32, len: i32)
        ptr for widget i is at memory address: 4 + i * 8
        return i32.load(4 + param[0] * 8)
        """
        instrs = (
            _i32_const(4)       # base of table
            + _local_get(0)     # i
            + _i32_const(8)
            + OP_I32_MUL        # i * 8
            + OP_I32_ADD        # 4 + i*8
            + OP_I32_LOAD       # load (align=2, offset=0)
            + b'\x02\x00'       # align, offset args
            + OP_RETURN
        )
        return self._encode_body([], instrs)

    def _fn_get_widget_len(self) -> bytes:
        """
        get_widget_len(i: i32) -> i32
        len for widget i is at memory address: 4 + i * 8 + 4
        return i32.load(8 + param[0] * 8)
        """
        instrs = (
            _i32_const(8)       # base + 4 offset for len field
            + _local_get(0)
            + _i32_const(8)
            + OP_I32_MUL
            + OP_I32_ADD
            + OP_I32_LOAD
            + b'\x02\x00'
            + OP_RETURN
        )
        return self._encode_body([], instrs)

    def _fn_render_all(self) -> bytes:
        """
        render_all() -> i32
        Returns the total byte count of all widget HTML strings combined.
        Computed statically as a constant.
        """
        total = sum(self._lengths)
        instrs = _i32_const(total) + OP_RETURN
        return self._encode_body([], instrs)

    # ── Data section ───────────────────────────────────────────────────────────

    def _data_section(self) -> bytes:
        """
        Active data segment at offset 0.
        Layout: [count: i32][ptr0: i32][len0: i32]...[html0 bytes][html1 bytes]...
        """
        count = len(self.widgets)

        # Header: count (4 bytes LE) + table entries (8 bytes each)
        header = struct.pack('<I', count)
        for off, ln in zip(self._offsets, self._lengths):
            header += struct.pack('<II', off, ln)

        # String data
        string_data = b''.join(self._strings)

        payload = header + string_data

        # Active segment: mode=0 (active, memory 0), offset expr, data bytes
        offset_expr = _i32_const(0) + OP_END
        seg = b'\x00' + offset_expr + _uleb128(len(payload)) + payload
        return _section(self.SEC_DATA, _vec([seg]))


# ── public API ─────────────────────────────────────────────────────────────────

def encode_wasm(widgets: List[Tuple[str, str]]) -> bytes:
    """
    Build a .wasm binary from a list of (widget_id, html_string) pairs.
    Returns raw bytes of a valid WebAssembly module.
    """
    return WASMModule(widgets).build()
