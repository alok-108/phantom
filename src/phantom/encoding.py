"""Phantom Encoding Subsystem.

Provides encoders and decoders for all four Phantom instruction encoding modes:
- Comment encoding (visible Python comments)
- Whitespace encoding (steganographic spaces and tabs)
- Unicode encoding (steganographic zero-width code points)
- Hybrid encoding (mixed-mode in a single source file)
"""

from __future__ import annotations

import unicodedata
from typing import Any

from phantom.grammar import (
    COMMENT_LINE_PATTERN,
    HYBRID_HEADER,
    WS_BEGIN_MARKER,
    WS_BIT_SPACE,
    WS_BIT_TAB,
    WS_BITS_PER_BYTE,
    WS_END_MARKER,
    ZW_BEGIN_MARKER,
    ZW_CHARS,
    ZW_CHARS_PER_BYTE,
    ZW_CHARS_REVERSE,
    ZW_END_MARKER,
    ZW_PERMITTED_CODEPOINTS,
    ZW_REJECTED_CODEPOINTS,
)
from phantom.ir import ArgumentType, EncodingMode, PhantomInstruction
from phantom.lines import split_physical_lines


def _instruction_to_text(instruction: str | PhantomInstruction) -> str:
    """Format a PhantomInstruction or string into standard instruction text."""
    if isinstance(instruction, PhantomInstruction):
        args_formatted = []
        for arg in instruction.arguments:
            if arg.type == ArgumentType.STRING:
                escaped = (
                    str(arg.value)
                    .replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t")
                )
                # Every other control character below U+0020 is escaped
                # too. A literal NUL in a comment line makes the whole
                # host file invalid Python, and the other controls are
                # invisible in a comment, so the text form never carries
                # any of them literally. The parser decodes \xNN back.
                for code in range(0x20):
                    if code in (0x09, 0x0A, 0x0D):
                        continue
                    escaped = escaped.replace(chr(code), f"\\x{code:02x}")
                args_formatted.append(f'"{escaped}"')
            else:
                args_formatted.append(str(arg.value))
        args_str = ", ".join(args_formatted)
        return f"phantom:{instruction.spec_version} {instruction.identifier}({args_str})"
    return instruction


# ──────────────────────────────────────────────────────────────────────
# Comment Encoder / Decoder
# ──────────────────────────────────────────────────────────────────────


class CommentEncoder:
    """Encodes Phantom instructions into Python comment lines."""

    @staticmethod
    def encode(instruction: PhantomInstruction) -> str:
        """Encode a PhantomInstruction into a comment string.

        Example output:
            #: phantom:0.1.0 event.declare("on_start")
        """
        raw_text = _instruction_to_text(instruction)
        return f"#: {raw_text}"


class CommentDecoder:
    """Decodes Phantom comment lines into instruction text or components."""

    @staticmethod
    def decode(comment_line: str) -> str:
        """Decode a comment line into raw instruction text.

        Example:
            '#: phantom:0.1.0 event.declare("on_start")'
            -> 'phantom:0.1.0 event.declare("on_start")'

        Raises:
            ValueError: If the line does not match COMMENT_LINE_PATTERN.
        """
        match = COMMENT_LINE_PATTERN.match(comment_line)
        if not match:
            raise ValueError(f"Invalid Phantom comment instruction line: {comment_line!r}")
        version = match.group(2)
        identifier = match.group(3)
        raw_args = match.group(4)
        return f"phantom:{version} {identifier}({raw_args})"

    @staticmethod
    def decode_parts(comment_line: str) -> tuple[str, str, str]:
        """Decode a comment line into (version, identifier, raw_args) tuple.

        Raises:
            ValueError: If the line does not match COMMENT_LINE_PATTERN.
        """
        match = COMMENT_LINE_PATTERN.match(comment_line)
        if not match:
            raise ValueError(f"Invalid Phantom comment instruction line: {comment_line!r}")
        return match.group(2), match.group(3), match.group(4)


# ──────────────────────────────────────────────────────────────────────
# Whitespace Encoder / Decoder
# ──────────────────────────────────────────────────────────────────────


class WhitespaceEncoder:
    """Encodes instruction text into whitespace-only lines (spaces and tabs)."""

    @staticmethod
    def encode(text: str | PhantomInstruction) -> list[str]:
        """Convert instruction text to a list of 8-character whitespace lines (1 line per byte).

        Bytes are encoded MSB first, with space = 0 and tab = 1.
        """
        raw_text = _instruction_to_text(text)
        utf8_bytes = raw_text.encode("utf-8")
        lines: list[str] = []
        for b in utf8_bytes:
            line_chars: list[str] = []
            for bit_idx in range(7, -1, -1):
                bit = (b >> bit_idx) & 1
                line_chars.append(WS_BIT_TAB if bit else WS_BIT_SPACE)
            lines.append("".join(line_chars))
        return lines

    @classmethod
    def encode_block(cls, text: str | PhantomInstruction) -> str:
        """Encode instruction text into a full whitespace block with markers."""
        lines = cls.encode(text)
        return "\n".join([WS_BEGIN_MARKER] + lines + [WS_END_MARKER])


class WhitespaceDecoder:
    """Decodes whitespace-only lines back into instruction text."""

    @staticmethod
    def decode(lines: list[str]) -> str:
        """Decode a list of whitespace-only lines into instruction text.

        Each line must be exactly 8 space/tab characters representing 1 byte.

        Raises:
            ValueError: If lines is empty, any line is not 8 chars,
                        contains invalid characters, or byte sequence is not valid UTF-8.
        """
        if not lines:
            raise ValueError("Whitespace block is empty (no data lines)")

        byte_array = bytearray()
        for line_idx, raw_line in enumerate(lines):
            line = raw_line.rstrip("\r\n")
            if len(line) != WS_BITS_PER_BYTE:
                raise ValueError(
                    f"Whitespace line {line_idx + 1} has length {len(line)}, "
                    f"expected exactly {WS_BITS_PER_BYTE}"
                )
            byte_val = 0
            for char_idx, ch in enumerate(line):
                if ch == WS_BIT_SPACE:
                    byte_val = (byte_val << 1) | 0
                elif ch == WS_BIT_TAB:
                    byte_val = (byte_val << 1) | 1
                else:
                    raise ValueError(
                        f"Whitespace line {line_idx + 1}, char {char_idx + 1}: "
                        f"invalid character {ch!r}, expected space or tab"
                    )
            byte_array.append(byte_val)

        try:
            return byte_array.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid UTF-8 payload in whitespace data: {e}") from e

    @classmethod
    def decode_block(cls, block_text: str) -> str:
        """Decode a full text containing #:ws:begin and #:ws:end markers."""
        lines: list[str] = []
        in_block = False
        found_block = False
        for line in split_physical_lines(block_text):
            stripped = line.strip()
            if stripped == WS_BEGIN_MARKER:
                in_block = True
                found_block = True
                continue
            if stripped == WS_END_MARKER:
                in_block = False
                break
            if in_block:
                lines.append(line)
        if not found_block:
            raise ValueError("No whitespace block start marker found")
        return cls.decode(lines)


# ──────────────────────────────────────────────────────────────────────
# Unicode Zero-Width Encoder / Decoder
# ──────────────────────────────────────────────────────────────────────


class UnicodeEncoder:
    """Encodes instruction text into zero-width Unicode characters."""

    @staticmethod
    def encode(text: str | PhantomInstruction) -> str:
        """Convert instruction text to a string of zero-width characters.

        Each byte is encoded as 4 zero-width characters (2 bits each, MSB first):
        U+200B = 00, U+200C = 01, U+200D = 10, U+FEFF = 11.
        """
        raw_text = _instruction_to_text(text)
        utf8_bytes = raw_text.encode("utf-8")
        chars: list[str] = []
        for b in utf8_bytes:
            for shift in (6, 4, 2, 0):
                two_bits = (b >> shift) & 0b11
                chars.append(ZW_CHARS_REVERSE[two_bits])
        return "".join(chars)

    @classmethod
    def encode_block(cls, text: str | PhantomInstruction) -> str:
        """Encode instruction text into a full zero-width block with markers."""
        zw_str = cls.encode(text)
        # The '# ' prefix keeps the data line a valid Python comment; bare
        # zero-width characters are a SyntaxError in the host program.
        return f"{ZW_BEGIN_MARKER}\n# {zw_str}\n{ZW_END_MARKER}"


class UnicodeDecoder:
    """Decodes zero-width Unicode characters back into instruction text."""

    @staticmethod
    def decode(zw_text: str, strict: bool = True) -> str:
        """Decode a string of zero-width characters into instruction text.

        Every 4 zero-width characters decode to 1 byte (UTF-8).

        Args:
            zw_text: String containing zero-width characters.
            strict: If True, reject non-permitted invisible characters and unknown chars.

        Raises:
            ValueError: If input is empty, contains rejected or unknown characters,
                        incomplete groups, or invalid UTF-8.
        """
        if not zw_text:
            raise ValueError("Zero-width data is empty")

        valid_chars: list[str] = []
        for idx, ch in enumerate(zw_text):
            if ch in ZW_REJECTED_CODEPOINTS:
                name = unicodedata.name(ch, "UNKNOWN")
                raise ValueError(
                    f"Rejected invisible Unicode code point at index {idx}: U+{ord(ch):04X} ({name})"
                )
            if ch in ZW_PERMITTED_CODEPOINTS:
                valid_chars.append(ch)
            else:
                if strict:
                    name = unicodedata.name(ch, "UNKNOWN")
                    raise ValueError(
                        f"Unknown or non-permitted character at index {idx}: U+{ord(ch):04X} ({name})"
                    )

        if not valid_chars:
            raise ValueError("No valid zero-width characters found in input")

        if len(valid_chars) % ZW_CHARS_PER_BYTE != 0:
            raise ValueError(
                f"Incomplete zero-width sequence: {len(valid_chars)} characters is not a multiple of {ZW_CHARS_PER_BYTE}"
            )

        byte_array = bytearray()
        for i in range(0, len(valid_chars), ZW_CHARS_PER_BYTE):
            b0 = ZW_CHARS[valid_chars[i]]
            b1 = ZW_CHARS[valid_chars[i + 1]]
            b2 = ZW_CHARS[valid_chars[i + 2]]
            b3 = ZW_CHARS[valid_chars[i + 3]]
            byte_val = (b0 << 6) | (b1 << 4) | (b2 << 2) | b3
            byte_array.append(byte_val)

        try:
            return byte_array.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid UTF-8 payload in zero-width data: {e}") from e

    @classmethod
    def decode_block(cls, block_text: str, strict: bool = True) -> str:
        """Decode a full block containing #:zw:begin and #:zw:end markers."""
        in_block = False
        found_block = False
        collected: list[str] = []
        for line in split_physical_lines(block_text):
            stripped = line.strip()
            if stripped == ZW_BEGIN_MARKER:
                in_block = True
                found_block = True
                continue
            if stripped == ZW_END_MARKER:
                in_block = False
                break
            if in_block:
                for ch in line:
                    if ch in ZW_PERMITTED_CODEPOINTS or ch in ZW_REJECTED_CODEPOINTS:
                        collected.append(ch)
        if not found_block:
            raise ValueError("No zero-width block start marker found")
        return cls.decode("".join(collected), strict=strict)


# ──────────────────────────────────────────────────────────────────────
# Hybrid Codec
# ──────────────────────────────────────────────────────────────────────


class HybridCodec:
    """Encoder and decoder for mixed-mode (hybrid) Phantom instructions."""

    @staticmethod
    def encode_instructions(
        instructions: list[PhantomInstruction],
        mode_map: dict[int, EncodingMode] | None = None,
        default_mode: EncodingMode = EncodingMode.COMMENT,
    ) -> str:
        """Encode multiple instructions into a single source using hybrid encoding."""
        lines: list[str] = [HYBRID_HEADER]
        for idx, inst in enumerate(instructions):
            mode = mode_map.get(idx) if mode_map else inst.source.encoding
            if mode == EncodingMode.HYBRID:
                mode = default_mode

            if mode == EncodingMode.COMMENT:
                lines.append(CommentEncoder.encode(inst))
            elif mode == EncodingMode.WHITESPACE:
                lines.append(WS_BEGIN_MARKER)
                lines.extend(WhitespaceEncoder.encode(inst))
                lines.append(WS_END_MARKER)
            elif mode == EncodingMode.UNICODE:
                lines.append(ZW_BEGIN_MARKER)
                lines.append(f"# {UnicodeEncoder.encode(inst)}")
                lines.append(ZW_END_MARKER)
            else:
                lines.append(CommentEncoder.encode(inst))
        return "\n".join(lines)

    @staticmethod
    def decode_instructions(source_text: str) -> list[str]:
        """Decode all instructions in source text, respecting precedence.

        Precedence: comment > whitespace > Unicode.
        Duplicate instructions from lower-precedence encodings are filtered out.
        """
        comment_instructions: list[str] = []
        ws_instructions: list[str] = []
        zw_instructions: list[str] = []

        lines = split_physical_lines(source_text)
        in_ws = False
        ws_lines: list[str] = []
        in_zw = False
        zw_chars: list[str] = []

        for raw_line in lines:
            line = raw_line.rstrip("\r")
            stripped = line.strip()

            if stripped == WS_BEGIN_MARKER:
                in_ws = True
                ws_lines = []
                continue
            if stripped == WS_END_MARKER:
                in_ws = False
                if ws_lines:
                    try:
                        decoded = WhitespaceDecoder.decode(ws_lines)
                        for d_line in split_physical_lines(decoded):
                            d_line = d_line.strip()
                            if d_line:
                                ws_instructions.append(d_line)
                    except ValueError:
                        pass
                ws_lines = []
                continue

            if stripped == ZW_BEGIN_MARKER:
                in_zw = True
                zw_chars = []
                continue
            if stripped == ZW_END_MARKER:
                in_zw = False
                if zw_chars:
                    try:
                        decoded = UnicodeDecoder.decode("".join(zw_chars), strict=True)
                        for d_line in split_physical_lines(decoded):
                            d_line = d_line.strip()
                            if d_line:
                                zw_instructions.append(d_line)
                    except ValueError:
                        pass
                zw_chars = []
                continue

            if in_ws:
                if all(c in " \t" for c in line):
                    ws_lines.append(line)
                continue

            if in_zw:
                for c in line:
                    if c in ZW_PERMITTED_CODEPOINTS or c in ZW_REJECTED_CODEPOINTS:
                        zw_chars.append(c)
                continue

            # Outside blocks: check comment instruction
            match = COMMENT_LINE_PATTERN.match(line)
            if match:
                comment_instructions.append(CommentDecoder.decode(line))

        # Apply precedence: comment > whitespace > Unicode
        seen: set[str] = set()
        results: list[str] = []

        for item in comment_instructions:
            if item not in seen:
                seen.add(item)
                results.append(item)

        for item in ws_instructions:
            if item not in seen:
                seen.add(item)
                results.append(item)

        for item in zw_instructions:
            if item not in seen:
                seen.add(item)
                results.append(item)

        return results


# ──────────────────────────────────────────────────────────────────────
# Top-level API functions
# ──────────────────────────────────────────────────────────────────────


def encode_instruction(
    instruction: PhantomInstruction,
    mode: EncodingMode = EncodingMode.COMMENT,
) -> str:
    """Encode a single PhantomInstruction into the requested encoding format."""
    if mode == EncodingMode.COMMENT:
        return CommentEncoder.encode(instruction)
    elif mode == EncodingMode.WHITESPACE:
        return WhitespaceEncoder.encode_block(instruction)
    elif mode == EncodingMode.UNICODE:
        return UnicodeEncoder.encode_block(instruction)
    elif mode == EncodingMode.HYBRID:
        return HybridCodec.encode_instructions([instruction])
    raise ValueError(f"Unsupported encoding mode: {mode}")


def decode_source(
    source_text: str,
    mode: EncodingMode | None = None,
) -> list[str]:
    """Decode instructions from source text.

    If mode is None or HYBRID, decodes across all formats according to hybrid precedence.
    If a specific mode is provided, decodes only that format.
    """
    if mode is None or mode == EncodingMode.HYBRID:
        return HybridCodec.decode_instructions(source_text)

    if mode == EncodingMode.COMMENT:
        results: list[str] = []
        for line in split_physical_lines(source_text):
            match = COMMENT_LINE_PATTERN.match(line)
            if match:
                results.append(CommentDecoder.decode(line))
        return results

    if mode == EncodingMode.WHITESPACE:
        results = []
        lines = split_physical_lines(source_text)
        in_ws = False
        ws_lines: list[str] = []
        for raw_line in lines:
            line = raw_line.rstrip("\r")
            stripped = line.strip()
            if stripped == WS_BEGIN_MARKER:
                in_ws = True
                ws_lines = []
                continue
            if stripped == WS_END_MARKER:
                in_ws = False
                if ws_lines:
                    decoded = WhitespaceDecoder.decode(ws_lines)
                    for d_line in split_physical_lines(decoded):
                        d_line = d_line.strip()
                        if d_line:
                            results.append(d_line)
                ws_lines = []
                continue
            if in_ws and all(c in " \t" for c in line):
                ws_lines.append(line)
        return results

    if mode == EncodingMode.UNICODE:
        results = []
        lines = split_physical_lines(source_text)
        in_zw = False
        zw_chars: list[str] = []
        for raw_line in lines:
            line = raw_line.rstrip("\r")
            stripped = line.strip()
            if stripped == ZW_BEGIN_MARKER:
                in_zw = True
                zw_chars = []
                continue
            if stripped == ZW_END_MARKER:
                in_zw = False
                if zw_chars:
                    decoded = UnicodeDecoder.decode("".join(zw_chars), strict=True)
                    for d_line in split_physical_lines(decoded):
                        d_line = d_line.strip()
                        if d_line:
                            results.append(d_line)
                zw_chars = []
                continue
            if in_zw:
                for c in line:
                    if c in ZW_PERMITTED_CODEPOINTS or c in ZW_REJECTED_CODEPOINTS:
                        zw_chars.append(c)
        return results

    raise ValueError(f"Unsupported encoding mode: {mode}")


def inspect_encoding(source_text: str) -> dict[str, Any]:
    """Inspect source text to detect which Phantom encoding modes are present."""
    has_hybrid_header = HYBRID_HEADER in source_text

    comment_count = 0
    for line in split_physical_lines(source_text):
        if COMMENT_LINE_PATTERN.match(line):
            comment_count += 1

    ws_block_count = source_text.count(WS_BEGIN_MARKER)
    zw_block_count = source_text.count(ZW_BEGIN_MARKER)

    has_comment = comment_count > 0
    has_ws = ws_block_count > 0
    has_zw = zw_block_count > 0

    encodings_detected: list[str] = []
    if has_comment:
        encodings_detected.append("comment")
    if has_ws:
        encodings_detected.append("whitespace")
    if has_zw:
        encodings_detected.append("unicode")

    detected_mode: EncodingMode | None = None
    if has_hybrid_header or len(encodings_detected) > 1:
        detected_mode = EncodingMode.HYBRID
    elif len(encodings_detected) == 1:
        detected_mode = EncodingMode(encodings_detected[0])

    return {
        "has_comment": has_comment,
        "has_whitespace": has_ws,
        "has_unicode": has_zw,
        "has_hybrid_header": has_hybrid_header,
        "comment_instruction_count": comment_count,
        "whitespace_block_count": ws_block_count,
        "unicode_block_count": zw_block_count,
        "encodings_detected": encodings_detected,
        "detected_mode": detected_mode,
    }
