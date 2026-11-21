import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

const filename = path.resolve(import.meta.dirname, "../lib/request-origin.ts");

function load(relative, calls) {
  const file = path.resolve(import.meta.dirname, "../app/api", relative);
  const source = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(file);
  loaded.require = name => {
    if (name === "@/lib/request-origin") return {
      rejectCrossOrigin: request => {
        const origin = request.headers.get("origin");
        const url = new URL(request.url);
        return origin === `${url.protocol}//${request.headers.get("host") ?? url.host}`
          ? null : Response.json({}, { status: 403 });
      },
    };
    if (name === "@/lib/backend-proxy") return {
      proxyBackendJson: async (...args) => { calls.push(args); return Response.json({ ok: true }); },
    };
    if (name === "next/server") return { NextResponse: { json: Response.json } };
    if (name === "next/headers") return { cookies: async () => ({ get: () => undefined }) };
    throw new Error(`Unexpected dependency ${name}`);
  };
  loaded._compile(source, file);
  return loaded.exports;
}

test("cookie-authenticated mutations require the exact browser origin", () => {
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename);
  loaded._compile(source, filename);
  const { isSameOriginRequest } = loaded.exports;
  const request = origin => new Request("http://localhost:3144/api/cases", {
    method: "POST", headers: { host: "127.0.0.1:3144", ...(origin ? { origin } : {}) },
  });
  assert.equal(isSameOriginRequest(request("http://127.0.0.1:3144")), true);
  for (const origin of [undefined, "http://localhost:3144", "https://127.0.0.1:3144", "https://other.example"]) {
    assert.equal(isSameOriginRequest(request(origin)), false);
  }
});

test("login preserves backend throttling status and retry time", async () => {
  const api = load("auth/login/route.ts", []);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(null, { status: 429, headers: { "Retry-After": "120" } });
  try {
    const request = new Request("http://127.0.0.1:3144/api/auth/login", {
      method: "POST", headers: { origin: "http://127.0.0.1:3144", host: "127.0.0.1:3144" },
      body: JSON.stringify({ email: "synthetic@example.test", password: "synthetic" }),
    });
    const response = await api.POST(request);
    assert.equal(response.status, 429);
    assert.equal(response.headers.get("Retry-After"), "120");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Case and Decision writes reject foreign origins before proxying", async () => {
  const id = "00000000-0000-0000-0000-000000000001";
  for (const [file, method, suffix, context] of [
    ["cases/route.ts", "POST", "cases", undefined],
    ["cases/[caseId]/route.ts", "PATCH", `cases/${id}`, { params: Promise.resolve({ caseId: id }) }],
    ["decisions/route.ts", "POST", "decisions", undefined],
  ]) {
    const calls = [];
    const api = load(file, calls);
    const request = origin => new Request(`http://127.0.0.1:3144/api/${suffix}`, {
      method, headers: origin ? { origin } : {}, body: "{}",
    });
    for (const origin of [undefined, "https://foreign.example"]) {
      assert.equal((await api[method](request(origin), context)).status, 403);
    }
    assert.equal(calls.length, 0);
    assert.equal((await api[method](request("http://127.0.0.1:3144"), context)).status, 200);
    assert.equal(calls.length, 1);
  }
});

test("login and logout reject foreign origins", async () => {
  for (const file of ["auth/login/route.ts", "auth/logout/route.ts"]) {
    const api = load(file, []);
    const request = new Request("http://127.0.0.1:3144/api/auth", {
      method: "POST", headers: { origin: "https://foreign.example" }, body: "{}",
    });
    assert.equal((await api.POST(request)).status, 403);
  }
});

test("login rejects malformed JSON without an internal error", async () => {
  const api = load("auth/login/route.ts", []);
  const request = new Request("http://127.0.0.1:3144/api/auth/login", {
    method: "POST", headers: { origin: "http://127.0.0.1:3144" }, body: "{",
  });
  assert.equal((await api.POST(request)).status, 400);
});
