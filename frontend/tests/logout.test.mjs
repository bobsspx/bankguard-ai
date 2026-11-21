import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

const filename = path.resolve(import.meta.dirname, "../app/api/auth/logout/route.ts");

function loadRoute(token, upstream) {
  const cookiesSet = [];
  const calls = [];
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename);
  loaded.require = name => {
    if (name === "next/server") return {
      NextResponse: { json: (body, options = {}) => ({ status: options.status ?? 200, body,
        cookies: { set: value => cookiesSet.push(value) } }) },
    };
    if (name === "next/headers") return { cookies: async () => ({ get: () => token ? { value: token } : undefined }) };
    if (name === "@/lib/request-origin") return { rejectCrossOrigin: request =>
      request.headers.get("origin") === new URL(request.url).origin ? null : { status: 403 } };
    throw new Error(`Unexpected dependency ${name}`);
  };
  loaded._compile(source, filename);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (...args) => { calls.push(args); return upstream(); };
  return { api: loaded.exports, calls, cookiesSet, restore: () => { globalThis.fetch = originalFetch; } };
}

const request = origin => new Request("http://127.0.0.1:3144/api/auth/logout", {
  method: "POST", headers: origin ? { origin } : {},
});

test("logout revokes backend session before removing browser cookie", async () => {
  const state = loadRoute("synthetic-token", () => ({ status: 200, ok: true }));
  try {
    const result = await state.api.POST(request("http://127.0.0.1:3144"));
    assert.equal(result.status, 200);
    assert.equal(state.calls.length, 1);
    assert.match(state.calls[0][0], /\/api\/v1\/auth\/logout$/);
    assert.equal(state.calls[0][1].headers.Authorization, "Bearer synthetic-token");
    assert.equal(state.cookiesSet[0].maxAge, 0);
  } finally { state.restore(); }
});

test("logout keeps cookie for retry when revocation fails", async () => {
  for (const upstream of [() => ({ status: 503, ok: false }), () => { throw new Error("offline"); }]) {
    const state = loadRoute("synthetic-token", upstream);
    try {
      assert.equal((await state.api.POST(request("http://127.0.0.1:3144"))).status, 503);
      assert.equal(state.cookiesSet.length, 0);
    } finally { state.restore(); }
  }
});

test("logout clears expired local cookie and blocks foreign origin", async () => {
  const expired = loadRoute("synthetic-token", () => ({ status: 401, ok: false }));
  try {
    assert.equal((await expired.api.POST(request("http://127.0.0.1:3144"))).status, 200);
    assert.equal(expired.cookiesSet[0].maxAge, 0);
    assert.equal((await expired.api.POST(request("https://foreign.example"))).status, 403);
    assert.equal(expired.calls.length, 1);
  } finally { expired.restore(); }
});
