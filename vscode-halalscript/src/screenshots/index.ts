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

async function reset(): Promise<void> {
  await cmd("workbench.action.closeAllEditors");
  await cmd("workbench.action.closePanel");
  await cmd("workbench.action.closeAuxiliaryBar");
  await cmd("hideSuggestWidget");
}


export async function run(): Promise<void> {
  await sleep(3000); // let the window settle
  await cmd("workbench.action.closeAuxiliaryBar");

  // 1. highlighting
  await reset();
  await open("zakat.halal");
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
  await open("zakat.halal", 5, 3);
  await cmd("editor.action.showHover");
  await shot("3-hover-ruling");

  // 4. completion with the keyword's documentation, and the snippets
  await reset();
  const editor = await open("zakat.halal", 16, 0);
  await editor.edit((e) => e.insert(new vscode.Position(16, 0), "\n"));
  editor.selection = new vscode.Selection(16, 0, 16, 0);
  await cmd("type", { text: "ist" });
  await cmd("editor.action.triggerSuggest");
  await sleep(800);
  await cmd("toggleSuggestionDetails");
  await shot("4-completion");
  await cmd("hideSuggestWidget");
  await cmd("workbench.action.files.revert");

  // 5. the syntax tree beside the program
  await reset();
  await open("zakat.halal");
  await cmd("halalscript.showAst");
  await shot("5-syntax-tree");

  // 6. Eastern Arabic numerals: the value on hover
  await reset();
  await open("zakat.halal", 5, 27);
  await cmd("editor.action.showHover");
  await shot("6-arabic-numeral");

  await reset();
}
