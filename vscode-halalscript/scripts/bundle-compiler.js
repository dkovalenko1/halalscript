// Copy the HalalScript compiler from the repository root into ./compiler, so
// the packaged extension carries its own copy and works outside the repository.

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const target = path.resolve(__dirname, "..", "compiler");

fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(path.join(target, "src"), { recursive: true });
fs.copyFileSync(path.join(root, "compiler.py"), path.join(target, "compiler.py"));
for (const name of fs.readdirSync(path.join(root, "src"))) {
  if (name.endsWith(".py")) {
    fs.copyFileSync(path.join(root, "src", name), path.join(target, "src", name));
  }
}
console.log(`bundled the compiler from ${root} into ${target}`);
