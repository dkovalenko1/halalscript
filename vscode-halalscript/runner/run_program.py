"""Compile a HalalScript program to LLVM IR and run it under lli, in a terminal.

    python run_program.py <compiler.py> <source.halal> <output.ll> <lli>

The extension's "Run the program" command starts this script as the process of
a terminal, so the program's sual() reads what is typed there. A missing
llvmlite or lli is reported in a sentence, and the terminal waits for Enter
before it closes, so the output stays readable.
"""

import shutil
import subprocess
import sys


def main() -> int:
    compiler, source, output, lli = sys.argv[1:5]
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
    return subprocess.run([lli, output]).returncode


if __name__ == "__main__":
    code = main()
    print(f"\n[the program ended with exit code {code}; press Enter to close]", end="", flush=True)
    try:
        input()
    except EOFError:
        pass
    sys.exit(code)
