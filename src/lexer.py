"""A hand-written state machine over the bytes of a HalalScript source.

lex() returns one token vector per source line that holds at least one token;
blank and comment-only lines produce no vector. Positions are 1-based; the
column counts characters (code points), so a two-byte Eastern Arabic digit is
one column wide. A byte that ends a token is not consumed: the machine goes
back to START and reads it again.
"""

from dataclasses import dataclass

from .errors import CompileError

I64_MAX = 2**63 - 1

# A keyword's token kind is its own spelling.
KEYWORDS = {
    word.encode(): word for word in (
        "wallahi", "bismillah", "inshallah",
        "dirham", "dinar", "fatwa",
        "halal", "haram",
        "istikhara", "qadarallah", "yalla", "khalas", "ameen",
        "la", "assalamu", "alaikum", "ma_dama",
    )
}
SINGLE_BYTE = {ord(c): c for c in "+-*(){}"}

LF, CR, SPACE, TAB = 10, 13, 32, 9
ARABIC_LEAD, ARABIC_ZERO, ARABIC_NINE = 0xD9, 0xA0, 0xA9  # U+0660..U+0669 is D9 A0..D9 A9


@dataclass(frozen=True)
class Token:
    kind: str  # a keyword, an operator spelling, "ident" or "number"
    text: str  # the source spelling
    line: int
    column: int
    value: int | None = None  # the value of a number


def is_letter(b: int) -> bool:
    return 65 <= b <= 90 or 97 <= b <= 122 or b == 95


def is_digit(b: int) -> bool:
    return 48 <= b <= 57


def is_continuation(b: int) -> bool:
    return 0x80 <= b <= 0xBF


class Lexer:
    def __init__(self, data: bytes):
        self.data = data
        self.i = 0  # index of the current byte
        self.line, self.col = 1, 1  # position of the character that starts at byte i
        self.lines: list[list[Token]] = []
        self.tokens: list[Token] = []
        self.start = self.start_line = self.start_col = 0  # where the current token began
        self.value = 0  # the value of the number being read

    def byte(self, offset: int = 0) -> int | None:
        j = self.i + offset
        return self.data[j] if j < len(self.data) else None

    def step(self):
        """Consume one byte; only the first byte of a character moves the column."""
        if not is_continuation(self.data[self.i]):
            self.col += 1
        self.i += 1

    def arabic_digit(self) -> int | None:
        """The value of the Eastern Arabic digit at the current byte, or None."""
        second = self.byte(1)
        if self.byte() == ARABIC_LEAD and second is not None and ARABIC_ZERO <= second <= ARABIC_NINE:
            return second - ARABIC_ZERO
        return None

    def mark(self):
        self.start, self.start_line, self.start_col = self.i, self.line, self.col

    def emit(self, kind: str, value: int | None = None):
        text = self.data[self.start:self.i].decode("utf-8")
        self.tokens.append(Token(kind, text, self.start_line, self.start_col, value))

    def error(self, message: str) -> CompileError:
        return CompileError(self.start_line, self.start_col, message)

    def lex(self) -> list[list[Token]]:
        state = "START"
        while True:
            b = self.byte()
            if state == "START":
                if b is None:
                    break
                if b == LF:
                    if self.tokens:
                        self.lines.append(self.tokens)
                    self.tokens = []
                    self.i += 1
                    self.line, self.col = self.line + 1, 1
                    continue
                if b in (SPACE, TAB, CR):
                    self.step()
                    continue
                self.mark()
                if b == ord("#"):
                    state = "COMMENT"
                    self.step()
                elif is_letter(b):
                    state = "IDENT"
                    self.step()
                elif is_digit(b):
                    state, self.value = "NUMBER", b - 48
                    self.step()
                elif (digit := self.arabic_digit()) is not None:
                    state, self.value = "ARABIC_NUMBER", digit
                    self.step()
                    self.step()
                elif b == ord(":"):
                    state = "COLON"
                    self.step()
                elif b == ord("="):
                    state = "EQUAL"
                    self.step()
                elif b == ord("!"):
                    state = "BANG"
                    self.step()
                elif b in SINGLE_BYTE:
                    self.step()
                    self.emit(SINGLE_BYTE[b])
                else:
                    raise self.unknown_character()

            elif state == "COMMENT":
                if b is None or b == LF:
                    state = "START"
                    continue
                self.i += 1  # any byte may stand in a comment; the column no longer matters

            elif state == "IDENT":
                if b is not None and (is_letter(b) or is_digit(b)):
                    self.step()
                    continue
                word = self.data[self.start:self.i]
                self.emit(KEYWORDS.get(word, "ident"))
                state = "START"

            elif state == "NUMBER":
                if b is not None and is_digit(b):
                    self.value = self.value * 10 + b - 48
                    self.step()
                    continue
                if self.arabic_digit() is not None:
                    raise self.error(self.MIXED_SCRIPTS)
                if b is not None and is_letter(b):
                    raise self.error(self.NUMBER_LETTERS)
                self.emit_number()
                state = "START"

            elif state == "ARABIC_NUMBER":
                if (digit := self.arabic_digit()) is not None:
                    self.value = self.value * 10 + digit
                    self.step()
                    self.step()
                    continue
                if b is not None and is_digit(b):
                    raise self.error(self.MIXED_SCRIPTS)
                if b is not None and is_letter(b):
                    raise self.error(self.NUMBER_LETTERS)
                self.emit_number()
                state = "START"

            elif state == "COLON":
                if b != ord("="):
                    raise self.error("':' must be followed by '=' — a colon alone assigns nothing "
                                     "and promises less")
                self.step()
                self.emit(":=")
                state = "START"

            elif state == "EQUAL":
                if b != ord("="):
                    raise self.error("a single '=' is not an operator — equality requires two "
                                     "witnesses: '=='; assignment is ':='")
                self.step()
                self.emit("==")
                state = "START"

            elif state == "BANG":
                if b != ord("="):
                    raise self.error("'!' alone is not an operator — negation is spoken plainly "
                                     "with 'la'")
                self.step()
                self.emit("!=")
                state = "START"

        if self.tokens:
            self.lines.append(self.tokens)
        return self.lines

    MIXED_SCRIPTS = "a numeral cannot serve two scripts — write it wholly in 0-9 or wholly in ٠-٩"
    NUMBER_LETTERS = "a numeral may not be adorned with letters or '_'"

    def emit_number(self):
        if self.value > I64_MAX:
            text = self.data[self.start:self.i].decode("utf-8")
            raise self.error(f"constant {text} exceeds even the dinar (i64) — this is riba, an "
                             "increase beyond every permitted measure")
        self.emit("number", self.value)

    def unknown_character(self) -> CompileError:
        """Describe the character at the current byte: a stranger, or not UTF-8 at all."""
        b = self.data[self.i]
        if b < 0x80:
            shown = f"'{chr(b)}'" if 33 <= b <= 126 else f"byte 0x{b:02X}"
            return self.error(f"the character {shown} appears in no scripture accepted by this "
                              "language")
        length = 2 if 0xC2 <= b <= 0xDF else 3 if 0xE0 <= b <= 0xEF else 4 if 0xF0 <= b <= 0xF4 else 0
        sequence = self.data[self.i:self.i + length]
        if length and len(sequence) == length and all(is_continuation(c) for c in sequence[1:]):
            try:
                char = sequence.decode("utf-8")
            except UnicodeDecodeError:  # overlong forms and surrogates
                pass
            else:
                return self.error(f"the character '{char}' appears in no scripture accepted by "
                                  "this language")
        return self.error(f"malformed UTF-8 byte 0x{b:02X} — the bytes are not in a state of "
                          "ritual purity")


def lex(data: bytes) -> list[list[Token]]:
    return Lexer(data).lex()
