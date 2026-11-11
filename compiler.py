"""The HalalScript compiler.

    python3 compiler.py input.txt output.ll  check the program and write its LLVM IR
    python3 compiler.py --ast input.txt      print the syntax tree
    python3 compiler.py --tokens input.txt   print the tokens, one per line
    python3 compiler.py input.txt            check the program and deliver a verdict

--optimize, anywhere on the line, runs the optimizer on the checked tree before
code generation; with --ast it prints the tree the optimizer left.

On an error: one line on stderr, `compilation error: line L:C: message`, exit
code 1, nothing on stdout and no output file. The output file is written only
after every phase has succeeded. llvmlite is needed only to write IR.
"""

import argparse
from pathlib import Path
import sys

from src.errors import CompileError
from src.lexer import lex
from src.optimizer import optimize
from src.parser import parse
from src.semantic import SemanticChecker

# Every pass walks a left-grouped chain such as 1 + 1 + ... one call per
# operator, so a long expression needs more than Python's default 1000 frames.
sys.setrecursionlimit(20000)


def main() -> int:
    parser = argparse.ArgumentParser(description="HalalScript compiler, stage 3")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ast", action="store_true", help="print the syntax tree")
    mode.add_argument("--tokens", action="store_true", help="print the tokens")
    parser.add_argument("--optimize", action="store_true",
                        help="remove unused variables and duas and inline duas called once")
    parser.add_argument("source", type=Path, help="path to the HalalScript program")
    parser.add_argument("output", type=Path, nargs="?", help="path of the LLVM IR file to write")
    args = parser.parse_args()
    if (args.ast or args.tokens) and args.output is not None:
        parser.error("--ast and --tokens take only the source path")
    if args.output is not None and args.output.suffix != ".ll":
        parser.error("the output file must have the .ll extension")

    try:
        data = args.source.read_bytes()
    except OSError as error:
        print(f"compilation error: cannot read '{args.source}': {error.strerror} — the scroll "
              "could not be found", file=sys.stderr)
        return 1
    try:
        lines = lex(data)
        if args.tokens:
            print("\n".join(f"{t.line}:{t.column} {t.kind} {t.text!r}"
                            for tokens in lines for t in tokens))
            return 0
        tree = parse(lines)
        if args.ast and not args.optimize:
            print(tree.dump())
            return 0
        tree.accept(SemanticChecker())
        if args.optimize:
            optimize(tree)
            if args.ast:
                print(tree.dump())
                return 0
        if args.output is None:
            print("The program is accepted: its syntax is sound, its types are lawful and its "
                  "greeting was returned.")
            return 0
        from src.codegen import generate  # llvmlite is imported only when IR is wanted
        ir_text = generate(tree)
    except CompileError as error:
        print(error, file=sys.stderr)
        return 1
    except RecursionError:
        print("compilation error: line 1:1: the program is nested too deeply to be judged — "
              "split its longest expression into several declarations", file=sys.stderr)
        return 1
    try:
        args.output.write_text(ir_text, encoding="utf-8")
    except OSError as error:
        print(f"compilation error: cannot write '{args.output}': {error.strerror}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
