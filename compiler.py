"""The HalalScript compiler front end (stage 1: lexer and parser).

    python3 compiler.py --ast input.txt      print the syntax tree
    python3 compiler.py --tokens input.txt   print the tokens, one per line
    python3 compiler.py input.txt            check the program and deliver a verdict

On an error: one line on stderr, `compilation error: line L:C: message`, exit
code 1 and nothing on stdout.
"""

import argparse
from pathlib import Path
import sys

from src.errors import CompileError
from src.lexer import lex
from src.parser import parse


def main() -> int:
    parser = argparse.ArgumentParser(description="HalalScript compiler, stage 1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ast", action="store_true", help="print the syntax tree")
    mode.add_argument("--tokens", action="store_true", help="print the tokens")
    parser.add_argument("source", type=Path, help="path to the HalalScript program")
    args = parser.parse_args()

    try:
        data = args.source.read_bytes()
    except OSError as error:
        print(f"compilation error: cannot read '{args.source}': {error.strerror} — the scroll "
              "could not be found", file=sys.stderr)
        return 1
    try:
        lines = lex(data)
        if args.tokens:
            output = "\n".join(f"{t.line}:{t.column} {t.kind} {t.text!r}"
                               for tokens in lines for t in tokens)
        else:
            tree = parse(lines)
            output = tree.dump() if args.ast else (
                "The program is accepted: its syntax is sound and its greeting was returned. "
                "Code generation arrives in a later stage.")
    except CompileError as error:
        print(error, file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
