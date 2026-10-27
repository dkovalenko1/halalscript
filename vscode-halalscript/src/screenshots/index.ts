// Runs inside VS Code: set up one scene per feature and capture the screen.

import { execFileSync } from "child_process";
import * as path from "path";
import * as vscode from "vscode";

const OUT = process.env.HALALSCRIPT_SHOTS!;
const FOLDER = vscode.workspace.workspaceFolders![0].uri.fsPath;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const cmd = (command: string, ...args: unknown[]) => vscode.commands.executeCommand(command, ...args);

const MENU_BAR = 33; // points of the macOS menu bar, left out of the capture

async function shot(name: string): Promise<void> {
  await cmd("notifications.clearAll");
  await sleep(1200);
  const file = path.join(OUT, `${name}.png`);
  // the main display's size in points, from a throwaway full capture
  execFileSync("screencapture", ["-x", file]);
  const size = execFileSync("sips", ["-g", "pixelWidth", "-g", "pixelHeight", file], { encoding: "utf8" });
  const [width, height] = [...size.matchAll(/: (\d+)/g)].map((m) => Number(m[1]) / 2);
  execFileSync("screencapture", ["-x", `-R0,${MENU_BAR},${width},${height - MENU_BAR}`, file]);
  console.log(`captured ${name}.png`);
}

async function open(name: string, line = 0, character = 0): Promise<vscode.TextEditor> {
  const document = await vscode.workspace.openTextDocument(path.join(FOLDER, name));
  const editor = await vscode.window.showTextDocument(document, { preview: false });
  editor.selection = new vscode.Selection(line, character, line, character);
  editor.revealRange(new vscode.Range(line, 0, line, 0), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
  return editor;
}

/** The position of the nth occurrence of text in a document, plus an offset into it. */
function find(editor: vscode.TextEditor, text: string, nth = 1, offset = 0): vscode.Position {
  const source = editor.document.getText();
  let index = -1;
  for (let i = 0; i < nth; i++) {
    index = source.indexOf(text, index + 1);
  }
  if (index < 0) {
    throw new Error(`'${text}' not found in ${editor.document.fileName}`);
  }
  return editor.document.positionAt(index + offset);
}

function place(editor: vscode.TextEditor, position: vscode.Position): void {
  editor.selection = new vscode.Selection(position, position);
  editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
}

async function reset(): Promise<void> {
  await cmd("workbench.action.closeAllEditors");
  await cmd("workbench.action.closePanel");
  await cmd("workbench.action.closeAuxiliaryBar");
  await cmd("hideSuggestWidget");
}


export async function run(): Promise<void> {
  await sleep(3000); // let the window settle
  await cmd("workbench.action.closeAuxiliaryBar");

  // 1. highlighting: diwans, duas, chains, sual, bayan and strings
  await reset();
  await open("treasury.halal");
  await shot("1-highlighting");

  // 2. a syntax error underlined, its message on hover and in Problems
  await reset();
  const broken = await open("broken_covenant.halal", 14, 2);
  await sleep(1500); // the compiler runs after the document opens
  await cmd("workbench.actions.view.problems");
  await vscode.window.showTextDocument(broken.document);
  broken.selection = new vscode.Selection(14, 2, 14, 2);
  await cmd("editor.action.showHover");
  await shot("2-compiler-error");

  // 3. the Official Ruling of a keyword on hover
  await reset();
  const diwanKeyword = await open("treasury.halal");
  place(diwanKeyword, find(diwanKeyword, "diwan Purse", 1, 2));
  await cmd("editor.action.showHover");
  await shot("3-hover-ruling");

  // 4. completion after a chain: the fields and member duas of the diwan it reaches
  await reset();
  const chain = await open("treasury.halal");
  const end = find(chain, "ameen zakat(t)");
  await chain.edit((e) => e.insert(end, "bayan(t.purse.)\n"));
  place(chain, end.translate(0, "bayan(t.purse.".length));
  await cmd("editor.action.triggerSuggest");
  await sleep(800);
  await cmd("toggleSuggestionDetails");
  await shot("4-completion");
  await cmd("hideSuggestWidget");
  await cmd("workbench.action.files.revert");

  // 5. the syntax tree beside the program
  await reset();
  await open("treasury.halal");
  await cmd("halalscript.showAst");
  await shot("5-syntax-tree");

  // 6. Eastern Arabic numerals: the value on hover
  await reset();
  await open("zakat.halal", 5, 27);
  await cmd("editor.action.showHover");
  await shot("6-arabic-numeral");

  // 7. a semantic error: a mutating dua called on a bismillah object
  await reset();
  const constant = await open("constant_object.halal");
  await sleep(1500);
  await cmd("workbench.actions.view.problems");
  await vscode.window.showTextDocument(constant.document);
  place(constant, find(constant, "deposit(50)", 1, 2));
  await cmd("editor.action.showHover");
  await shot("7-semantic-error");

  // 8. a dua's signature on hover over its call
  await reset();
  const call = await open("treasury.halal");
  place(call, find(call, "ameen zakat(t)", 1, 8));
  await cmd("editor.action.showHover");
  await shot("8-hover-dua");

  // 9. running the program: the terminal reads sual() from what is typed
  await reset();
  await open("treasury.halal");
  await cmd("halalscript.runProgram");
  await sleep(2500);
  const terminal = vscode.window.terminals.find((t) => t.name === "HalalScript: treasury.halal");
  terminal?.sendText("120000 2000");
  await sleep(2500);
  await shot("9-run-program");
  terminal?.sendText("");
  terminal?.dispose();

  await reset();
}
