// Integration tests: run inside a real VS Code with the extension loaded.

import * as assert from "assert";
import * as path from "path";
import * as vscode from "vscode";

const FIXTURES = path.resolve(__dirname, "..", "..", "..", "test", "fixtures");

async function open(name: string): Promise<vscode.TextEditor> {
  const document = await vscode.workspace.openTextDocument(path.join(FIXTURES, name));
  return vscode.window.showTextDocument(document);
}

/** Wait until the compiler has reported on the document (an empty list counts). */
async function diagnosticsOf(uri: vscode.Uri, want: (d: vscode.Diagnostic[]) => boolean) {
  for (let i = 0; i < 100; i++) {
    const found = vscode.languages.getDiagnostics(uri);
    if (want(found)) {
      return found;
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error("timed out waiting for diagnostics: " + JSON.stringify(vscode.languages.getDiagnostics(uri)));
}

function hoverText(hovers: vscode.Hover[]): string {
  return hovers
    .flatMap((h) => h.contents)
    .map((c) => (typeof c === "string" ? c : (c as vscode.MarkdownString).value))
    .join("\n");
}

describe("HalalScript extension", () => {
  after(async () => {
    await vscode.commands.executeCommand("workbench.action.closeAllEditors");
  });

  it("recognises .halal files as HalalScript", async () => {
    const editor = await open("good.halal");
    assert.strictEqual(editor.document.languageId, "halalscript");
  });

  it("reports no error for a valid program", async () => {
    const editor = await open("good.halal");
    // give the compiler time to run, then expect an empty verdict
    await new Promise((r) => setTimeout(r, 1500));
    assert.deepStrictEqual(vscode.languages.getDiagnostics(editor.document.uri), []);
  });

  it("underlines the closer of a broken covenant with the compiler's message", async () => {
    const editor = await open("mismatched.halal");
    const [diagnostic] = await diagnosticsOf(editor.document.uri, (d) => d.length > 0);
    assert.strictEqual(diagnostic.severity, vscode.DiagnosticSeverity.Error);
    assert.strictEqual(diagnostic.source, "HalalScript");
    assert.match(diagnostic.message, /'yalla' at 3:17 must be closed by 'khalas', not '\}'/);
    assert.deepStrictEqual(
      [diagnostic.range.start.line, diagnostic.range.start.character, diagnostic.range.end.character],
      [4, 0, 1],
    );
  });

  it("underlines a character outside the BMP with its full UTF-16 width", async () => {
    const editor = await open("astral_error.halal");
    const [diagnostic] = await diagnosticsOf(editor.document.uri, (d) => d.length > 0);
    assert.match(diagnostic.message, /appears in no scripture/);
    assert.deepStrictEqual(
      [diagnostic.range.start.line, diagnostic.range.start.character, diagnostic.range.end.character],
      [1, 27, 29],
    );
  });

  it("re-checks unsaved edits and clears the error once fixed", async () => {
    const editor = await open("mismatched.halal");
    await diagnosticsOf(editor.document.uri, (d) => d.length > 0);
    await editor.edit((e) => e.replace(new vscode.Range(4, 0, 4, 1), "khalas"));
    await diagnosticsOf(editor.document.uri, (d) => d.length === 0);
    await editor.edit((e) => e.replace(new vscode.Range(4, 0, 4, 6), "}"));
    await diagnosticsOf(editor.document.uri, (d) => d.length > 0);
  });

  it("shows the Official Ruling on hover over a keyword", async () => {
    const editor = await open("good.halal");
    const hovers = await vscode.commands.executeCommand<vscode.Hover[]>(
      "vscode.executeHoverProvider", editor.document.uri, new vscode.Position(3, 3));
    const text = hoverText(hovers);
    assert.match(text, /\*\*bismillah\*\* — immutable variable/);
    assert.match(text, /Official Ruling/);
  });

  it("shows a variable's declaration and an Arabic numeral's value on hover", async () => {
    const editor = await open("good.halal");
    const onTotal = await vscode.commands.executeCommand<vscode.Hover[]>(
      "vscode.executeHoverProvider", editor.document.uri, new vscode.Position(7, 2));
    assert.match(hoverText(onTotal), /mutable dinar, declared on line 5/);
    const onDigits = await vscode.commands.executeCommand<vscode.Hover[]>(
      "vscode.executeHoverProvider", editor.document.uri, new vscode.Position(3, 23));
    assert.match(hoverText(onDigits), /Eastern Arabic numeral: \*\*12\*\*/);
  });

  it("offers no hover inside a comment", async () => {
    const editor = await open("good.halal");
    const line = editor.document.lineAt(2).text;
    const hovers = await vscode.commands.executeCommand<vscode.Hover[]>(
      "vscode.executeHoverProvider", editor.document.uri, new vscode.Position(2, line.indexOf("constant") + 1));
    assert.strictEqual(hoverText(hovers), "");
  });

  it("completes keywords and declared names", async () => {
    const editor = await open("good.halal");
    const list = await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider", editor.document.uri, new vscode.Position(16, 0));
    const labels = list.items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
    for (const want of ["istikhara", "qadarallah", "wallahi", "ameen", "total", "LIMIT"]) {
      assert.ok(labels.includes(want), `missing completion '${want}'`);
    }
  });

  it("offers the snippets for a typed prefix", async () => {
    const document = await vscode.workspace.openTextDocument(
      { language: "halalscript", content: "assalamu alaikum\nisti\nameen 0\n" });
    await vscode.window.showTextDocument(document);
    const list = await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider", document.uri, new vscode.Position(1, 4));
    const snippets = list.items
      .filter((i) => i.kind === vscode.CompletionItemKind.Snippet)
      .map((i) => (typeof i.label === "string" ? i.label : i.label.label));
    assert.ok(snippets.includes("istikhara"), "snippets offered: " + JSON.stringify(snippets));
    assert.ok(snippets.includes("istikhara-qadarallah"), "snippets offered: " + JSON.stringify(snippets));
  });

  it("converts the number under the cursor to Eastern Arabic digits and back", async () => {
    const editor = await open("digits.halal");
    editor.selection = new vscode.Selection(1, 26, 1, 26);
    await vscode.commands.executeCommand("halalscript.toArabicDigits");
    assert.strictEqual(editor.document.lineAt(1).text, "bismillah dirham year := ١٤٤٦");
    editor.selection = new vscode.Selection(1, 0, 1, editor.document.lineAt(1).text.length);
    await vscode.commands.executeCommand("halalscript.toWesternDigits");
    assert.strictEqual(editor.document.lineAt(1).text, "bismillah dirham year := 1446");
    await vscode.commands.executeCommand("workbench.action.files.revert");
  });

  it("jumps between yalla and its khalas like a bracket pair", async () => {
    const editor = await open("good.halal");
    editor.selection = new vscode.Selection(9, 14, 9, 14); // inside 'yalla'
    await vscode.commands.executeCommand("editor.action.jumpToBracket");
    assert.strictEqual(editor.selection.active.line, 11, "did not jump to 'khalas'");
  });

  it("indents after yalla, outdents khalas and toggles '#' comments", async () => {
    const document = await vscode.workspace.openTextDocument(
      { language: "halalscript", content: "assalamu alaikum\nistikhara halal yalla" });
    const editor = await vscode.window.showTextDocument(document);
    editor.options = { insertSpaces: true, tabSize: 4 };
    editor.selection = new vscode.Selection(1, 21, 1, 21);
    await vscode.commands.executeCommand("type", { text: "\n" });
    assert.strictEqual(document.lineAt(2).text, "    ");
    await vscode.commands.executeCommand("type", { text: "ameen 1\nkhalas" });
    await vscode.commands.executeCommand("editor.action.reindentlines");
    assert.strictEqual(document.lineAt(3).text, "khalas");
    editor.selection = new vscode.Selection(0, 0, 0, 0);
    await vscode.commands.executeCommand("editor.action.commentLine");
    assert.strictEqual(document.lineAt(0).text, "# assalamu alaikum");
  });

  it("opens the syntax tree beside the program", async () => {
    await open("good.halal");
    await vscode.commands.executeCommand("halalscript.showAst");
    const tree = vscode.window.visibleTextEditors.find((e) => e.document.isUntitled);
    assert.ok(tree, "no syntax tree editor opened");
    assert.match(tree.document.getText(), /^Program\n  Decl LIMIT dinar wallahi \(constant\)/);
    assert.match(tree.document.getText(), /Int 12 \(١٢\)/);
  });
});
