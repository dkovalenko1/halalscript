// Download a VS Code build and run the integration suite inside it, with the
// extension under development loaded and test/fixtures opened as the workspace.

import * as path from "path";
import { runTests } from "@vscode/test-electron";

async function main(): Promise<void> {
  const extensionDevelopmentPath = path.resolve(__dirname, "..", "..");
  // Inherited from a host that is itself an Electron app, this variable would
  // start VS Code as plain Node.js instead of as the editor.
  delete process.env.ELECTRON_RUN_AS_NODE;
  try {
    await runTests({
      extensionDevelopmentPath,
      extensionTestsPath: path.resolve(__dirname, "suite", "index"),
      launchArgs: [
        path.join(extensionDevelopmentPath, "test", "fixtures"),
        "--disable-extensions",
        "--disable-workspace-trust",
      ],
    });
  } catch {
    console.error("integration tests failed");
    process.exit(1);
  }
}

void main();
