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

  // ---------- stage 2: diwans, duas, sual, bayan ----------

  async function hoverAt(editor: vscode.TextEditor, line: number, word: string, nth = 1): Promise<string> {
    const text = editor.document.lineAt(line).text;
    let column = -1;
    for (let i = 0; i < nth; i++) {
      column = text.indexOf(word, column + 1);
    }
    assert.ok(column >= 0, `'${word}' not on line ${line}`);
    const hovers = await vscode.commands.executeCommand<vscode.Hover[]>(
      "vscode.executeHoverProvider", editor.document.uri, new vscode.Position(line, column + 1));
    return hoverText(hovers);
  }

  async function completionLabels(editor: vscode.TextEditor, line: number, column: number): Promise<string[]> {
    const list = await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider", editor.document.uri, new vscode.Position(line, column));
    return list.items
      .filter((i) => i.kind !== vscode.CompletionItemKind.Snippet && i.kind !== vscode.CompletionItemKind.Text)
      .map((i) => (typeof i.label === "string" ? i.label : i.label.label));
  }

  it("reports no error for a program with diwans, duas and bayan", async () => {
    const editor = await open("stage2.halal");
    await new Promise((r) => setTimeout(r, 1500));
    assert.deepStrictEqual(vscode.languages.getDiagnostics(editor.document.uri), []);
  });

  it("underlines a semantic error: a mutating dua called on a bismillah object", async () => {
    const editor = await open("constant_object.halal");
    const [diagnostic] = await diagnosticsOf(editor.document.uri, (d) => d.length > 0);
    assert.match(diagnostic.message, /cannot call mutating dua 'deposit' on 't\.purse': 't' is immutable/);
    const start = editor.document.lineAt(17).text.indexOf("deposit");
    assert.deepStrictEqual(
      [diagnostic.range.start.line, diagnostic.range.start.character, diagnostic.range.end.character],
      [17, start, start + "deposit".length],
    );
  });

  it("shows the Official Ruling of dua, diwan and bayan on hover", async () => {
    const editor = await open("stage2.halal");
    assert.match(await hoverAt(editor, 13, "dua"), /\*\*dua\*\* — function/);
    assert.match(await hoverAt(editor, 1, "diwan"), /\*\*diwan\*\* — structure/);
    assert.match(await hoverAt(editor, 18, "bayan"), /\*\*bayan\*\* — print/);
  });

  it("shows a dua's signature, a diwan's fields and a field reached through a chain", async () => {
    const editor = await open("stage2.halal");
    assert.match(await hoverAt(editor, 19, "zakat"), /dua dinar zakat\(Treasury t\)/);
    assert.match(await hoverAt(editor, 17, "deposit"), /member dua of diwan Purse/);
    const diwan = await hoverAt(editor, 16, "Treasury", 2);
    assert.match(diwan, /inshallah Purse purse/);
    assert.match(diwan, /diwan with 2 fields and 0 member duas/);
    assert.match(await hoverAt(editor, 14, "coins"), /mutable field of diwan Purse/);
    assert.match(await hoverAt(editor, 14, "rate"), /immutable field of diwan Treasury/);
  });

  it("resolves a name inside a member dua: a field, a parameter, never a top-level name", async () => {
    const editor = await open("stage2.halal");
    assert.match(await hoverAt(editor, 5, "coins", 2), /mutable field of this diwan/);
    assert.match(await hoverAt(editor, 5, "amount"), /parameter of dua deposit/);
    assert.match(await hoverAt(editor, 14, "t"), /parameter of dua zakat/);
  });

  it("completes only the fields and member duas of the diwan a chain reaches", async () => {
    const editor = await open("stage2.halal");
    const line = editor.document.lineAt(14).text;
    const sorted = async (column: number) => (await completionLabels(editor, 14, column)).sort();
    assert.deepStrictEqual(await sorted(line.indexOf("purse")), ["purse", "rate"]);
    assert.deepStrictEqual(await sorted(line.indexOf("coins")), ["coins", "deposit", "owner"]);
  });

  it("completes duas and diwans, and inside a dua only the names it can see", async () => {
    const editor = await open("stage2.halal");
    const top = await completionLabels(editor, 19, 0);
    for (const want of ["zakat", "Treasury", "Purse", "t", "total", "dua", "diwan", "bayan", "sual"]) {
      assert.ok(top.includes(want), `missing completion '${want}'`);
    }
    const inside = await completionLabels(editor, 14, 4);
    assert.ok(inside.includes("t") && inside.includes("zakat"), JSON.stringify(inside));
    assert.ok(!inside.includes("total"), "a dua cannot see the top-level 'total'");
    const member = await completionLabels(editor, 5, 8);
    for (const want of ["coins", "owner", "amount", "deposit"]) {
      assert.ok(member.includes(want), `missing completion '${want}' inside a member dua`);
    }
  });

  it("forgets a declaration once its block closes, like the compiler", async () => {
    const editor = await open("block_scope.halal");
    assert.match(await hoverAt(editor, 7, "p"), /immutable dirham, declared on line 7/);
    assert.match(await hoverAt(editor, 9, "p"), /immutable Point, declared on line 5/);
    const line = editor.document.lineAt(9).text;
    assert.deepStrictEqual(await completionLabels(editor, 9, line.indexOf("x")), ["x"]);
  });

  it("offers the diwan and dua snippets for a typed prefix", async () => {
    const document = await vscode.workspace.openTextDocument(
      { language: "halalscript", content: "assalamu alaikum\ndi\ndu\nameen 0\n" });
    await vscode.window.showTextDocument(document);
    const snippetsAt = async (line: number) => {
      const list = await vscode.commands.executeCommand<vscode.CompletionList>(
        "vscode.executeCompletionItemProvider", document.uri, new vscode.Position(line, 2));
      return list.items
        .filter((i) => i.kind === vscode.CompletionItemKind.Snippet)
        .map((i) => (typeof i.label === "string" ? i.label : i.label.label));
    };
    const diwan = await snippetsAt(1);
    assert.ok(diwan.includes("diwan") && diwan.includes("diwan{"), "snippets offered: " + JSON.stringify(diwan));
    const dua = await snippetsAt(2);
    assert.ok(dua.includes("dua") && dua.includes("dua{"), "snippets offered: " + JSON.stringify(dua));
  });

  it("runs the program in a terminal of its own", async () => {
    await open("stage2.halal");
    await vscode.commands.executeCommand("halalscript.runProgram");
    const terminal = vscode.window.terminals.find((t) => t.name === "HalalScript: stage2.halal");
    assert.ok(terminal, "no terminal: " + JSON.stringify(vscode.window.terminals.map((t) => t.name)));
    terminal.dispose();
  });
});
