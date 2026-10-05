// HalalScript for VS Code: live compiler verdicts, keyword rulings on hover,
// completion, Eastern Arabic digit conversion and an --ast viewer. Highlighting,
// snippets, comments and indentation are declared in package.json.

import * as crypto from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

import { codePointColumnToOffset, CompilerError, runCompiler } from "./compiler";
import { numberAround, toArabicDigits, toWesternDigits } from "./digits";
import { KEYWORD_BY_WORD, KEYWORDS, keywordMarkdown } from "./keywords";

const LANGUAGE = "halalscript";
const DEBOUNCE_MS = 300;
const DECLARATION =
  /^\s*(wallahi|bismillah|inshallah)\s+(dirham|dinar|fatwa)\s+([A-Za-z_][A-Za-z0-9_]*)/;
const KIND_FLAG: Record<string, string> = {
  wallahi: "constant",
  bismillah: "immutable",
  inshallah: "mutable",
};

let extensionContext: vscode.ExtensionContext;
let failureShown = false;

export function activate(context: vscode.ExtensionContext): void {
  extensionContext = context;
  const diagnostics = vscode.languages.createDiagnosticCollection(LANGUAGE);
  const timers = new Map<string, NodeJS.Timeout>();

  const schedule = (document: vscode.TextDocument, delay: number) => {
    if (document.languageId !== LANGUAGE) {
      return;
    }
    const key = document.uri.toString();
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(() => {
      timers.delete(key);
      void refreshDiagnostics(document, diagnostics);
    }, delay));
  };

  context.subscriptions.push(
    diagnostics,
    vscode.workspace.onDidOpenTextDocument((d) => schedule(d, 0)),
    vscode.workspace.onDidChangeTextDocument((e) => schedule(e.document, DEBOUNCE_MS)),
    vscode.workspace.onDidSaveTextDocument((d) => schedule(d, 0)),
    vscode.workspace.onDidCloseTextDocument((d) => {
      diagnostics.delete(d.uri);
      fs.rm(tempPath(d), { force: true }, () => undefined);
    }),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration(LANGUAGE)) {
        failureShown = false;
        vscode.workspace.textDocuments.forEach((d) => schedule(d, 0));
      }
    }),
    vscode.languages.registerHoverProvider(LANGUAGE, { provideHover }),
    vscode.languages.registerCompletionItemProvider(LANGUAGE, { provideCompletionItems }),
    vscode.commands.registerCommand("halalscript.toArabicDigits", () => convertDigits(toArabicDigits)),
    vscode.commands.registerCommand("halalscript.toWesternDigits", () => convertDigits(toWesternDigits)),
    vscode.commands.registerCommand("halalscript.showAst", showAst),
  );
  vscode.workspace.textDocuments.forEach((d) => schedule(d, 0));
}

export function deactivate(): void {}

// ---------- the compiler ----------

function settings() {
  const config = vscode.workspace.getConfiguration(LANGUAGE);
  const configured = config.get<string>("compilerPath", "").trim();
  return {
    python: config.get<string>("pythonPath", "python3"),
    compiler: configured || extensionContext.asAbsolutePath(path.join("compiler", "compiler.py")),
    diagnostics: config.get<boolean>("diagnostics.enabled", true),
  };
}

/** The compiler reads a file, so the unsaved text goes to a temporary copy. */
function tempPath(document: vscode.TextDocument): string {
  const id = crypto.createHash("sha1").update(document.uri.toString()).digest("hex").slice(0, 12);
  return path.join(os.tmpdir(), `halalscript-${id}.halal`);
}

async function compile(document: vscode.TextDocument, args: string[]) {
  const file = tempPath(document);
  await fs.promises.writeFile(file, document.getText(), "utf8");
  const { python, compiler } = settings();
  return runCompiler(python, compiler, [...args, file]);
}

function reportFailure(reason: string) {
  if (!failureShown) {
    failureShown = true;
    void vscode.window.showWarningMessage(
      `HalalScript: the compiler could not be consulted (${reason}). ` +
        "Check the halalscript.pythonPath and halalscript.compilerPath settings.",
    );
  }
}

async function refreshDiagnostics(
  document: vscode.TextDocument,
  diagnostics: vscode.DiagnosticCollection,
): Promise<void> {
  if (document.isClosed) {
    return;
  }
  if (!settings().diagnostics) {
    diagnostics.delete(document.uri);
    return;
  }
  const version = document.version;
  const result = await compile(document, []);
  if (document.isClosed || document.version !== version) {
    return; // a newer edit has its own run scheduled
  }
  if (result.failure) {
    reportFailure(result.failure);
    diagnostics.delete(document.uri);
    return;
  }
  if (!result.error) {
    diagnostics.set(document.uri, []);
    return;
  }
  const diagnostic = new vscode.Diagnostic(
    errorRange(document, result.error),
    result.error.message,
    vscode.DiagnosticSeverity.Error,
  );
  diagnostic.source = "HalalScript";
  diagnostics.set(document.uri, [diagnostic]);
}

/** Underline the token the compiler pointed at: a word, a number, an operator or one character. */
export function errorRange(document: vscode.TextDocument, error: CompilerError): vscode.Range {
  const line = Math.min(Math.max(error.line - 1, 0), document.lineCount - 1);
  const text = document.lineAt(line).text;
  const start = codePointColumnToOffset(text, error.column);
  if (start >= text.length) {
    // "found end of line": mark the last character of the line
    return new vscode.Range(line, Math.max(text.length - 1, 0), line, text.length);
  }
  const position = new vscode.Position(line, start);
  const word = document.getWordRangeAtPosition(position);
  if (word && word.start.isEqual(position)) {
    return word;
  }
  const two = text.slice(start, start + 2);
  const length = [":=", "==", "!="].includes(two) ? 2 : text.codePointAt(start)! > 0xffff ? 2 : 1;
  return new vscode.Range(position, position.translate(0, length));
}

// ---------- hover and completion ----------

function inComment(lineText: string, offset: number): boolean {
  const hash = lineText.indexOf("#");
  return hash !== -1 && hash < offset;
}

interface Declaration {
  name: string;
  kind: string;
  type: string;
  line: number;
}

function declarations(document: vscode.TextDocument): Declaration[] {
  const found: Declaration[] = [];
  for (let line = 0; line < document.lineCount; line++) {
    const match = DECLARATION.exec(document.lineAt(line).text);
    if (match) {
      found.push({ kind: match[1], type: match[2], name: match[3], line });
    }
  }
  return found;
}

function provideHover(document: vscode.TextDocument, position: vscode.Position) {
  const range = document.getWordRangeAtPosition(position);
  if (!range || inComment(document.lineAt(position.line).text, range.start.character)) {
    return undefined;
  }
  const word = document.getText(range);
  const keyword = KEYWORD_BY_WORD.get(word);
  if (keyword) {
    return new vscode.Hover(new vscode.MarkdownString(keywordMarkdown(keyword)), range);
  }
  if (/^[٠-٩]+$/.test(word)) {
    return new vscode.Hover(`Eastern Arabic numeral: **${toWesternDigits(word)}**`, range);
  }
  // The nearest declaration above the cursor (shadowing aside, a good guess).
  const declaration = declarations(document)
    .filter((d) => d.name === word && d.line <= position.line)
    .pop();
  if (declaration) {
    const markdown = new vscode.MarkdownString();
    markdown.appendCodeblock(`${declaration.kind} ${declaration.type} ${declaration.name}`, LANGUAGE);
    markdown.appendMarkdown(
      `${KIND_FLAG[declaration.kind]} ${declaration.type}, declared on line ${declaration.line + 1}`,
    );
    return new vscode.Hover(markdown, range);
  }
  return undefined;
}

function provideCompletionItems(document: vscode.TextDocument, position: vscode.Position) {
  if (inComment(document.lineAt(position.line).text, position.character)) {
    return [];
  }
  const items = KEYWORDS.map((k) => {
    const item = new vscode.CompletionItem(k.word, vscode.CompletionItemKind.Keyword);
    item.detail = k.role;
    item.documentation = new vscode.MarkdownString(keywordMarkdown(k));
    return item;
  });
  const seen = new Set<string>();
  for (const d of declarations(document)) {
    if (seen.has(d.name)) {
      continue;
    }
    seen.add(d.name);
    const kind = d.kind === "wallahi" ? vscode.CompletionItemKind.Constant : vscode.CompletionItemKind.Variable;
    const item = new vscode.CompletionItem(d.name, kind);
    item.detail = `${d.kind} ${d.type} (${KIND_FLAG[d.kind]})`;
    items.push(item);
  }
  return items;
}

// ---------- commands ----------

async function convertDigits(convert: (text: string) => string): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return;
  }
  const document = editor.document;
  await editor.edit((edit) => {
    for (const selection of editor.selections) {
      let range: vscode.Range | undefined = selection;
      if (selection.isEmpty) {
        const line = document.lineAt(selection.active.line).text;
        const around = numberAround(line, selection.active.character);
        range = around && new vscode.Range(selection.active.line, around[0], selection.active.line, around[1]);
      }
      if (range) {
        edit.replace(range, convert(document.getText(range)));
      }
    }
  });
}

async function showAst(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== LANGUAGE) {
    void vscode.window.showInformationMessage("HalalScript: open a .halal file to see its syntax tree.");
    return;
  }
  const result = await compile(editor.document, ["--ast"]);
  if (result.failure) {
    reportFailure(result.failure);
    return;
  }
  if (result.error) {
    void vscode.window.showErrorMessage(
      `HalalScript: line ${result.error.line}:${result.error.column}: ${result.error.message}`,
    );
    return;
  }
  const tree = await vscode.workspace.openTextDocument({ content: result.stdout, language: "plaintext" });
  await vscode.window.showTextDocument(tree, { viewColumn: vscode.ViewColumn.Beside, preview: true });
}
