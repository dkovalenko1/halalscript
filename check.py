"""Run every test program through the compiler and print a PASS/FAIL table.

tests/ok/*.txt   must compile to .ll, run under lli, and print exactly the
                 .expected file next to it; NAME.in, when it exists, is the
                 program's standard input. When NAME.ast exists, the --ast
                 output must equal it as well.
tests/err/*.txt  must be rejected: a non-zero exit code, nothing on stdout, no
                 output file, and stderr equal to the .expected file
examples/*.halal must compile and run

Run it with the Python that has llvmlite installed. LLI=/path/to/lli picks the
interpreter; by default it is lli on PATH, then Homebrew's LLVM.
Exit status 0 only when every test passes.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"
TESTS = ROOT / "tests"
LLI_CANDIDATES = ["/opt/homebrew/opt/llvm/bin/lli", "/usr/local/opt/llvm/bin/lli"]


def find_lli() -> str | None:
    if "LLI" in os.environ:
        return os.environ["LLI"]
    return shutil.which("lli") or next((p for p in LLI_CANDIDATES if Path(p).exists()), None)


def run(command, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                          input=stdin, timeout=30)


def compiler(*args) -> subprocess.CompletedProcess:
    return run([sys.executable, "-B", str(COMPILER), *args])


def compile_and_run(source: Path, work: Path, lli: str) -> tuple[str | None, str]:
    """(reason, stdout): reason is None when the program compiled and ran."""
    output = work / (source.stem + ".ll")
    result = compiler(str(source), str(output))
    if result.returncode != 0:
        return "rejected: " + result.stderr.strip(), ""
    stdin_file = source.with_suffix(".in")
    stdin = stdin_file.read_text(encoding="utf-8") if stdin_file.exists() else None
    executed = run([lli, str(output)], stdin)
    if executed.stderr:
        return "lli: " + executed.stderr.strip().splitlines()[0], executed.stdout
    return None, executed.stdout


def check_ok(source: Path, work: Path, lli: str) -> str | None:
    expected = source.with_suffix(".expected")
    if not expected.exists():
        return f"missing {expected.name}"
    tree = source.with_suffix(".ast")
    if tree.exists():
        result = compiler("--ast", str(source))
        if result.returncode != 0 or result.stdout != tree.read_text(encoding="utf-8"):
            return f"--ast differs from {tree.name}"
    reason, stdout = compile_and_run(source, work, lli)
    if reason:
        return reason
    if stdout != expected.read_text(encoding="utf-8"):
        got = stdout.strip().splitlines()
        return f"output differs from {expected.name}: got {got[-1] if got else 'nothing'!r}"
    return None


def check_err(source: Path, work: Path, lli: str) -> str | None:
    expected = source.with_suffix(".expected")
    if not expected.exists():
        return f"missing {expected.name}"
    output = work / (source.stem + ".ll")
    result = compiler(str(source), str(output))
    if result.returncode == 0:
        return "accepted, but must be rejected"
    if result.stdout:
        return "printed output despite the error"
    if output.exists():
        return "wrote an output file despite the error"
    if result.stderr != expected.read_text(encoding="utf-8"):
        return "reported " + result.stderr.strip()
    return None


def check_example(source: Path, work: Path, lli: str) -> str | None:
    return compile_and_run(source, work, lli)[0]


def main() -> int:
    lli = find_lli()
    if lli is None:
        print("lli was not found: install LLVM or set LLI=/path/to/lli", file=sys.stderr)
        return 2
    rows = []
    suites = [("ok", check_ok, TESTS / "ok", "*.txt"),
              ("err", check_err, TESTS / "err", "*.txt"),
              ("examples", check_example, ROOT / "examples", "*.halal")]
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for suite, check, folder, pattern in suites:
            for source in sorted(folder.glob(pattern)):
                reason = check(source, work, lli)
                rows.append((suite, source.stem, "PASS" if reason is None else "FAIL", reason or ""))

    widths = [max(len(row[i]) for row in rows + [("suite", "test", "result", "")]) for i in range(3)]
    for row in [("suite", "test", "result", "reason"),
                tuple("-" * w for w in widths) + ("",), *rows]:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)), row[3])

    failed = [row for row in rows if row[2] == "FAIL"]
    print(f"\n{len(rows) - len(failed)}/{len(rows)} passed")
    if failed:
        print("failed: " + ", ".join(f"{suite}/{name}" for suite, name, _, _ in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
