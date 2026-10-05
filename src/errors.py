"""The one error type every phase raises."""


class CompileError(Exception):
    """A lexical or syntax error at a source position.

    str() gives the line the compiler prints:
    compilation error: line L:C: message
    """

    def __init__(self, line: int, column: int, message: str):
        self.line, self.column, self.message = line, column, message
        super().__init__(f"compilation error: line {line}:{column}: {message}")
