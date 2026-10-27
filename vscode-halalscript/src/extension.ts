// HalalScript for VS Code: live compiler verdicts, keyword rulings on hover,
// completion (also of fields and member duas after '.'), Eastern Arabic digit
// conversion, an --ast viewer and a command that runs the program. Highlighting,
// snippets, comments and indentation are declared in package.json.

import * as crypto from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

import { codePointColumnToOffset, CompilerError, runCompiler } from "./compiler";
import { numberAround, toArabicDigits, toWesternDigits } from "./digits";
import { KEYWORD_BY_WORD, KEYWORDS, keywordMarkdown } from "./keywords";
import {
  chainBefore, Diwan, diwanOfChain, Dua, duaAt, duaNamed, KIND_FLAG, ownFieldAt, scan, signature, Symbols,
  variableAt,
} from "./symbols";

const LANGUAGE = "halalscript";
const DEBOUNCE_MS = 300;

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
    vscode.languages.registerCompletionItemProvider(LANGUAGE, { provideCompletionItems }, "."),
    vscode.commands.registerCommand("halalscript.toArabicDigits", () => convertDigits(toArabicDigits)),
    vscode.commands.registerCommand("halalscript.toWesternDigits", () => convertDigits(toWesternDigits)),
    vscode.commands.registerCommand("halalscript.showAst", showAst),
    vscode.commands.registerCommand("halalscript.runProgram", runProgram),
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
    lli: config.get<string>("lliPath", "lli"),
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

function symbolsOf(document: vscode.TextDocument): Symbols {
  const lines: string[] = [];
  for (let line = 0; line < document.lineCount; line++) {
    lines.push(document.lineAt(line).text);
  }
  return scan(lines);
}

function codeHover(code: string, text: string, range: vscode.Range): vscode.Hover {
  const markdown = new vscode.MarkdownString();
  markdown.appendCodeblock(code, LANGUAGE);
  markdown.appendMarkdown(text);
  return new vscode.Hover(markdown, range);
}

function duaHover(dua: Dua, range: vscode.Range): vscode.Hover {
  const where = dua.owner ? `member dua of diwan ${dua.owner}` : "dua";
  return codeHover(signature(dua), `${where}, declared on line ${dua.line + 1}`, range);
}

function diwanHover(diwan: Diwan, range: vscode.Range): vscode.Hover {
  const lines = [`diwan ${diwan.name}`, ...diwan.fields.map((f) => `    ${f.kind} ${f.type} ${f.name}`),
    ...diwan.duas.map((d) => `    ${signature(d)}`)];
  const duas = diwan.duas.length === 1 ? "1 member dua" : `${diwan.duas.length} member duas`;
  const fields = diwan.fields.length === 1 ? "1 field" : `${diwan.fields.length} fields`;
  return codeHover(lines.join("\n"), `diwan with ${fields} and ${duas}, declared on line ${diwan.line + 1}`, range);
}

function provideHover(document: vscode.TextDocument, position: vscode.Position) {
  const range = document.getWordRangeAtPosition(position);
  const lineText = document.lineAt(position.line).text;
  if (!range || inComment(lineText, range.start.character)) {
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
  const symbols = symbolsOf(document);
  const line = position.line;
  const called = /^\s*\(/.test(lineText.slice(range.end.character));
  // after a '.': a field or a member dua of the diwan the chain reaches
  const member = chainBefore(lineText, range.start.character);
  if (member && member.partial === "") {
    const diwan = diwanOfChain(symbols, member.chain, line);
    const dua = called && diwan?.duas.find((d) => d.name === word);
    if (dua) {
      return duaHover(dua, range);
    }
    const field = diwan?.fields.find((f) => f.name === word);
    if (field) {
      return codeHover(`${field.kind} ${field.type} ${field.name}`,
        `${KIND_FLAG[field.kind]} field of diwan ${diwan!.name}, declared on line ${field.line + 1}`, range);
    }
    return undefined;
  }
  if (called) {
    const diwan = symbols.diwans.get(word);
    if (diwan) {
      return diwanHover(diwan, range);
    }
    const dua = duaNamed(symbols, word, line);
    return dua ? duaHover(dua, range) : undefined;
  }
  const variable = variableAt(symbols, word, line);
  if (variable) {
    if (variable.kind === "parameter") {
      return codeHover(`${variable.type} ${variable.name}`,
        `parameter of dua ${variable.dua!.name} (a copy, immutable) ${variable.type}`, range);
    }
    return codeHover(`${variable.kind} ${variable.type} ${variable.name}`,
      `${KIND_FLAG[variable.kind]} ${variable.type}, declared on line ${variable.line + 1}`, range);
  }
  const field = ownFieldAt(symbols, word, line);
  if (field) {
    return codeHover(`${field.kind} ${field.type} ${field.name}`,
      `${KIND_FLAG[field.kind]} field of this diwan, declared on line ${field.line + 1}`, range);
  }
  const diwan = symbols.diwans.get(word);
  if (diwan) {
    return diwanHover(diwan, range);
  }
  const dua = duaNamed(symbols, word, line);
  return dua ? duaHover(dua, range) : undefined;
}

function duaItem(dua: Dua, kind: vscode.CompletionItemKind): vscode.CompletionItem {
  const item = new vscode.CompletionItem(dua.name, kind);
  item.detail = signature(dua);
  item.insertText = new vscode.SnippetString(dua.params.length ? `${dua.name}($1)` : `${dua.name}()`);
  return item;
}

function provideCompletionItems(document: vscode.TextDocument, position: vscode.Position) {
  const lineText = document.lineAt(position.line).text;
  if (inComment(lineText, position.character)) {
    return [];
  }
  const symbols = symbolsOf(document);
  const line = position.line;
  // after 'chain.': only the fields and the member duas of the diwan it reaches
  const member = chainBefore(lineText, position.character);
  if (member) {
    const diwan = diwanOfChain(symbols, member.chain, line);
    if (!diwan) {
      return [];
    }
    const fields = diwan.fields.map((f) => {
      const item = new vscode.CompletionItem(f.name, vscode.CompletionItemKind.Field);
      item.detail = `${f.kind} ${f.type} (${KIND_FLAG[f.kind]} field of ${diwan.name})`;
      return item;
    });
    return [...fields, ...diwan.duas.map((d) => duaItem(d, vscode.CompletionItemKind.Method))];
  }
  const items = KEYWORDS.map((k) => {
    const item = new vscode.CompletionItem(k.word, vscode.CompletionItemKind.Keyword);
    item.detail = k.role;
    item.documentation = new vscode.MarkdownString(keywordMarkdown(k));
    return item;
  });
  const seen = new Set<string>();
  const add = (item: vscode.CompletionItem) => {
    const label = typeof item.label === "string" ? item.label : item.label.label;
    if (!seen.has(label)) {
      seen.add(label);
      items.push(item);
    }
  };
  // the names this line can see: its own dua's names, or the top level's
  const dua = duaAt(symbols, line);
  const here = symbols.variables.filter((v) => v.line <= line && v.dua === dua);
  for (const v of here.reverse()) {
    const kind = v.kind === "wallahi" ? vscode.CompletionItemKind.Constant : vscode.CompletionItemKind.Variable;
    const item = new vscode.CompletionItem(v.name, kind);
    item.detail = v.kind === "parameter" ? `parameter ${v.type} (immutable)` : `${v.kind} ${v.type} (${KIND_FLAG[v.kind]})`;
    add(item);
  }
  const owner = dua?.owner;
  const ownDiwan = owner ? symbols.diwans.get(owner) : undefined;
  for (const f of ownDiwan?.fields ?? []) {
    const item = new vscode.CompletionItem(f.name, vscode.CompletionItemKind.Field);
    item.detail = `${f.kind} ${f.type} (${KIND_FLAG[f.kind]} field of ${ownDiwan!.name})`;
    add(item);
  }
  for (const d of ownDiwan?.duas ?? []) {
    add(duaItem(d, vscode.CompletionItemKind.Method));
  }
  for (const d of symbols.duas.filter((d) => !d.owner)) {
    add(duaItem(d, vscode.CompletionItemKind.Function));
  }
  for (const diwan of symbols.diwans.values()) {
    const item = new vscode.CompletionItem(diwan.name, vscode.CompletionItemKind.Struct);
    item.detail = `diwan ${diwan.name}(${diwan.fields.map((f) => `${f.type} ${f.name}`).join(", ")})`;
    add(item);
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

/**
 * Compile the program to LLVM IR and run it under lli in a terminal, so that
 * sual() reads what is typed there. The runner script reports a missing
 * llvmlite or lli in words rather than as a traceback.
 */
async function runProgram(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== LANGUAGE) {
    void vscode.window.showInformationMessage("HalalScript: open a .halal file to run it.");
    return;
  }
  if (!vscode.workspace.isTrusted) {
    void vscode.window.showWarningMessage(
      "HalalScript: a program is run only in a trusted workspace — trust this folder to run it.");
    return;
  }
  const document = editor.document;
  const source = tempPath(document);
  await fs.promises.writeFile(source, document.getText(), "utf8");
  const { python, compiler, lli } = settings();
  const runner = extensionContext.asAbsolutePath(path.join("runner", "run_program.py"));
  const title = `HalalScript: ${path.basename(document.fileName)}`;
  vscode.window.terminals.filter((t) => t.name === title).forEach((t) => t.dispose());
  const terminal = vscode.window.createTerminal({
    name: title,
    shellPath: python,
    shellArgs: ["-B", runner, compiler, source, source.replace(/\.halal$/, ".ll"), lli],
  });
  terminal.show();
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
