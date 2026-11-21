import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

const filename = path.resolve(import.meta.dirname, "../lib/logout-client.ts");

function load() {
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename);
  loaded._compile(source, filename);
  return loaded.exports.revokeAndLogout;
}

test("successful revocation redirects to login", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true });
  const calls = [];
  try {
    await load()({ replace: value => calls.push(value), refresh: () => calls.push("refresh") }, value => calls.push(value));
    assert.deepEqual(calls, ["/login", "refresh"]);
  } finally { globalThis.fetch = originalFetch; }
});

test("failed or unavailable revocation stays on page with error", async () => {
  const originalFetch = globalThis.fetch;
  try {
    for (const response of [() => ({ ok: false }), () => { throw new Error("offline"); }]) {
      globalThis.fetch = response;
      const calls = [];
      await load()({ replace: value => calls.push(value), refresh: () => calls.push("refresh") }, value => calls.push(value));
      assert.equal(calls.length, 1);
      assert.match(calls[0], /revoke|logout|session/i);
    }
  } finally { globalThis.fetch = originalFetch; }
});
