"""Run every test program through the compiler and print a PASS/FAIL table.

tests/ok/*.txt   must parse: exit code 0, empty stderr, and the --ast output
                 equal to the .ast file next to the program
tests/err/*.txt  must be rejected: a non-zero exit code, nothing on stdout, and
                 stderr equal to the .expected file next to the program

Exit status 0 only when every test passes.
"""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"
TESTS = ROOT / "tests"


def run_ast(source: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(COMPILER), "--ast", str(source)],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)


def check_ok(source: Path) -> str | None:
    """None when the program passes, otherwise a one-line reason."""
    expected = source.with_suffix(".ast")
    if not expected.exists():
        return f"missing {expected.name}"
    result = run_ast(source)
    if result.returncode != 0:
        return "rejected: " + result.stderr.strip()
    if result.stderr:
        return "wrote to stderr: " + result.stderr.strip()
    if result.stdout != expected.read_text(encoding="utf-8"):
        return f"--ast differs from {expected.name}"
    return None


def check_err(source: Path) -> str | None:
    expected = source.with_suffix(".expected")
    if not expected.exists():
        return f"missing {expected.name}"
    result = run_ast(source)
    if result.returncode == 0:
        return "accepted, but must be rejected"
    if result.stdout:
        return "printed output despite the error"
    if result.stderr != expected.read_text(encoding="utf-8"):
        return "reported " + result.stderr.strip()
    return None


def main() -> int:
    rows = []
    for suite, check in (("ok", check_ok), ("err", check_err)):
        for source in sorted((TESTS / suite).glob("*.txt")):
            reason = check(source)
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
