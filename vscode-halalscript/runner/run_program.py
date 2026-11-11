"""Compile a HalalScript program to LLVM IR and run it under lli, in a terminal.

    python run_program.py <compiler.py> <source.halal> <output.ll> <lli> <name>

The extension's "Run the program" command starts this script as the process of
a terminal, so the program's sual() reads what is typed there. It first says
what it runs, and asks for the input when the program calls sual(), since a
program waiting for input shows nothing else. A missing llvmlite or lli is
reported in a sentence, and the terminal waits for Enter before it closes, so
the output stays readable.
"""

import re
import shutil
import subprocess
import sys

# sual( outside a comment and a string literal
READS_INPUT = re.compile(r'^[^#"]*(?:"[^"]*"[^#"]*)*\bsual\s*\(', re.MULTILINE)


def main() -> int:
    compiler, source, output, lli, name = sys.argv[1:6]
    try:
        import llvmlite  # noqa: F401  (the compiler needs it to write IR)
    except ImportError:
        print(f"llvmlite is not installed for {sys.executable}. Install it there "
              "(pip install llvmlite), or point halalscript.pythonPath at a Python that has it.")
        return 1
    if shutil.which(lli) is None:
        print(f"'{lli}' was not found. Install LLVM, or point halalscript.lliPath at lli.")
        return 1
    if subprocess.run([sys.executable, "-B", compiler, source, output]).returncode != 0:
        return 1
    print(f"[running {name}]")
    with open(source, encoding="utf-8") as file:
        if READS_INPUT.search(file.read()):
            print("[it reads its input with sual(): type the numbers, separated by spaces or "
                  "new lines, and press Enter]")
    sys.stdout.flush()
    return subprocess.run([lli, output]).returncode


if __name__ == "__main__":
    code = main()
    print(f"\n[the program ended with exit code {code}; press Enter to close]", end="", flush=True)
    try:
        input()
    except EOFError:
        pass
    sys.exit(code)
