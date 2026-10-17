// Launch the downloaded VS Code with the extension and a trusted showcase
// folder, and let ./index take one screenshot per feature into ./images.
// macOS only (it uses screencapture). Run: npm run screenshots

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { runTests } from "@vscode/test-electron";

async function main(): Promise<void> {
  const root = path.resolve(__dirname, "..", "..");
  delete process.env.ELECTRON_RUN_AS_NODE; // see src/test/runTest.ts

  const userData = fs.mkdtempSync(path.join(os.tmpdir(), "halalscript-shots-"));
  fs.mkdirSync(path.join(userData, "User"), { recursive: true });
  fs.writeFileSync(path.join(userData, "User", "settings.json"), JSON.stringify({
    "workbench.colorTheme": "Default Dark Modern",
    "workbench.startupEditor": "none",
    "workbench.tips.enabled": false,
    "workbench.secondarySideBar.defaultVisibility": "hidden",
    "workbench.layoutControl.enabled": false,
    "chat.commandCenter.enabled": false,
    "chat.disableAIFeatures": true,
    "window.newWindowDimensions": "maximized",
    "window.commandCenter": false,
    "editor.fontSize": 16,
    "editor.minimap.enabled": false,
    "editor.hover.delay": 100,
    "editor.suggest.showStatusBar": false,
    "security.workspace.trust.enabled": false,
    "update.mode": "none",
    "git.enabled": false,
    "git.openRepositoryInParentFolders": "never",
    "telemetry.telemetryLevel": "off",
  }, null, 2));

  process.env.HALALSCRIPT_SHOTS = path.join(root, "images");
  await runTests({
    extensionDevelopmentPath: root,
    extensionTestsPath: path.resolve(__dirname, "index"),
    launchArgs: [
      path.join(root, "test", "showcase"),
      "--disable-extensions",
      "--user-data-dir", userData,
    ],
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
