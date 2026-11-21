import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

const filename = path.resolve(import.meta.dirname, "../lib/navigation.ts");
function load() {
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename);
  loaded._compile(source, filename);
  return loaded.exports;
}

test("navigation uses backend permissions, including the existing security analyst role", () => {
  const { visibleNavigation } = load();
  assert.deepEqual(visibleNavigation(["security.monitor"]).map(item => item.href), ["/security"]);
  assert.deepEqual(visibleNavigation(["transactions.read", "cases.read"]).map(item => item.href), ["/", "/cases"]);
  assert.equal(visibleNavigation(["*"]).length, 5);
  assert.deepEqual(visibleNavigation([]), []);
});
