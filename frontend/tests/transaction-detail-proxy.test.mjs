import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

const filename = path.resolve(import.meta.dirname, "../app/api/transactions/[transactionId]/route.ts");
const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

function route() {
  const calls = [];
  const loaded = new Module(filename);
  loaded.require = name => name === "next/server"
    ? { NextResponse: { json: (body, options) => Response.json(body, options) } }
    : name === "@/lib/backend-proxy"
      ? { proxyBackendGet: async path => { calls.push(path); return Response.json({ ok: true }); } }
      : (() => { throw new Error(`Unexpected import ${name}`); })();
  loaded._compile(source, filename);
  return { GET: loaded.exports.GET, calls };
}

test("transaction detail proxy forwards only valid UUIDs to the guarded backend", async () => {
  const id = "00000000-0000-0000-0000-000000000001";
  const { GET, calls } = route();
  const context = transactionId => ({ params: Promise.resolve({ transactionId }) });
  assert.equal((await GET(new Request("http://localhost/"), context("../security"))).status, 400);
  assert.equal(calls.length, 0);
  assert.equal((await GET(new Request("http://localhost/"), context(id))).status, 200);
  assert.deepEqual(calls, [`/api/v1/transactions/${id}`]);
});
