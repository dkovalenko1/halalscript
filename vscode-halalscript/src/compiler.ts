// Running the HalalScript compiler and reading its verdict.

import { execFile } from "child_process";

export interface CompilerError {
  line: number; // 1-based, as the compiler prints it
  column: number; // 1-based, counted in code points
  message: string;
}

export interface CompilerResult {
  ok: boolean;
  stdout: string;
  error?: CompilerError;
  failure?: string; // the compiler could not be run, or printed something unexpected
}

const ERROR_LINE = /^compilation error: line (\d+):(\d+): (.*)$/;

/** Parse `compilation error: line L:C: message`, or return undefined. */
export function parseErrorLine(stderr: string): CompilerError | undefined {
  const match = ERROR_LINE.exec(stderr.trim());
  if (!match) {
    return undefined;
  }
  return { line: Number(match[1]), column: Number(match[2]), message: match[3] };
}

/**
 * The compiler counts columns in code points; VS Code counts UTF-16 units.
 * Return the 0-based UTF-16 offset of the 1-based code-point column.
 */
export function codePointColumnToOffset(lineText: string, column: number): number {
  let offset = 0;
  let seen = 1;
  for (const char of lineText) {
    if (seen === column) {
      return offset;
    }
    offset += char.length;
    seen++;
  }
  return offset; // past the end: the column right after the last character
}

export function runCompiler(
  python: string,
  compiler: string,
  args: string[],
  timeoutMs = 5000,
): Promise<CompilerResult> {
  return new Promise((resolve) => {
    execFile(
      python,
      ["-B", compiler, ...args],
      { timeout: timeoutMs, encoding: "utf8" },
      (err, stdout, stderr) => {
        if (!err) {
          resolve({ ok: true, stdout });
          return;
        }
        const error = parseErrorLine(stderr);
        if (error) {
          resolve({ ok: false, stdout, error });
          return;
        }
        const reason = (err as NodeJS.ErrnoException).code === "ENOENT"
          ? `'${python}' was not found`
          : stderr.trim() || err.message;
        resolve({ ok: false, stdout, failure: reason });
      },
    );
  });
}
