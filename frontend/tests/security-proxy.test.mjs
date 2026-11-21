import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import ts from "typescript";

function route(relative) {
  const calls = [];
  const filename = path.resolve(import.meta.dirname, "../app/api/security/alerts/[alertId]", relative);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename);
  loaded.require = name => {
    if (name === "@/lib/request-origin") return {
      rejectCrossOrigin: request => {
        const url = new URL(request.url);
        const expected = `${url.protocol}//${request.headers.get("host") ?? url.host}`;
        return request.headers.get("origin") === expected ? null : Response.json({}, { status: 403 });
      },
    };
    assert.equal(name, "@/lib/backend-proxy");
    return {
      proxyBackendGet: async (...args) => { calls.push(args); return Response.json({ ok: true }); },
      proxyBackendJson: async (...args) => { calls.push(args); return Response.json({ ok: true }); },
    };
  };
  loaded._compile(source, filename);
  return { api: loaded.exports, calls };
}

const id = "00000000-0000-0000-0000-000000000001";
const context = value => ({ params: Promise.resolve({ alertId: value }) });
const url = `http://localhost:3000/api/security/alerts/${id}`;

test("PATCH validates browser origin against Host when Next normalizes its internal URL", async () => {
  for (const [origin, expected] of [["http://127.0.0.1:3144", 200], ["http://localhost:3144", 403], ["https://other.example", 403], ["https://127.0.0.1:3144", 403]]) {
    const { api, calls } = route("route.ts");
    const request = new Request(`http://localhost:3144/api/security/alerts/${id}`, {
      method: "PATCH", headers: { host: "127.0.0.1:3144", origin }, body: "{}",
    });
    assert.equal((await api.PATCH(request, context(id))).status, expected);
    assert.equal(calls.length, expected === 200 ? 1 : 0);
  }
});

test("invalid identifiers cannot change the upstream route", async () => {
  const { api, calls } = route("route.ts");
  assert.equal((await api.GET(new Request(url), context("../auth"))).status, 422);
  assert.equal(calls.length, 0);
});

test("GET uses fixed security detail path", async () => {
  const { api, calls } = route("route.ts");
  assert.equal((await api.GET(new Request(url), context(id))).status, 200);
  assert.deepEqual(calls, [[`/api/v1/security/alerts/${id}`]]);
});

test("PATCH rejects cross-origin and missing-origin requests before forwarding", async () => {
  for (const origin of [undefined, "https://other.example"]) {
    const { api, calls } = route("route.ts");
    const headers = origin ? { origin } : {};
    assert.equal((await api.PATCH(new Request(url, { method: "PATCH", headers, body: "{}" }), context(id))).status, 403);
    assert.equal(calls.length, 0);
  }
});

test("PATCH rejects malformed JSON", async () => {
  const { api, calls } = route("route.ts");
  const request = new Request(url, { method: "PATCH", headers: { origin: "http://localhost:3000" }, body: "{" });
  assert.equal((await api.PATCH(request, context(id))).status, 400);
  assert.equal(calls.length, 0);
});

test("PATCH preserves expected status and reason for backend validation", async () => {
  const { api, calls } = route("route.ts");
  const body = { status: "investigating", expected_status: "open", reason: "Check evidence" };
  const request = new Request(url, { method: "PATCH", headers: { origin: "http://localhost:3000" }, body: JSON.stringify(body) });
  assert.equal((await api.PATCH(request, context(id))).status, 200);
  assert.deepEqual(calls, [[`/api/v1/security/alerts/${id}`, "PATCH", body]]);
});

test("history only forwards pagination parameters to a fixed route", async () => {
  const { api, calls } = route("history/route.ts");
  await api.GET(new Request(url + "/history?limit=10&offset=20&url=https://other.example"), context(id));
  assert.deepEqual(calls, [[`/api/v1/security/alerts/${id}/history?limit=10&offset=20`]]);
});
