import assert from "node:assert/strict";
import test from "node:test";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
require("typescript");
// The installed tsx loader is used by the frontend test script.
const { readTransactionQuery, transactionQuery } = await import("../lib/transaction-query.ts");

test("transaction filters and pagination survive a URL round trip", () => {
  const params = transactionQuery({ account: " A-1 ", country: "la", channel: "web", minAmount: "12.50" }, 25);
  assert.equal(params.get("limit"), "25");
  assert.equal(params.get("account_ref"), "A-1");
  assert.equal(params.get("country_code"), "LA");
  assert.equal(readTransactionQuery(params).offset, 25);
  assert.equal(readTransactionQuery(new URLSearchParams("offset=-1")).offset, 0);
});

test("a previous filter URL restores input and page after clearing", () => {
  const previous = transactionQuery({ account: "BG-ACC-003", country: "LA", channel: "", minAmount: "" }, 25);
  const cleared = transactionQuery({ account: "", country: "", channel: "", minAmount: "" }, 0);
  assert.equal(readTransactionQuery(cleared).filters.account, "");
  assert.deepEqual(readTransactionQuery(previous), {
    filters: { account: "BG-ACC-003", country: "LA", channel: "", minAmount: "" },
    offset: 25,
    sortBy: "occurred_at",
    sortDir: "desc",
  });
});

test("sorting survives URL round trips with filters and pages", () => {
  const filters = { account: "BG-ACC-003", country: "", channel: "web", minAmount: "" };
  const query = transactionQuery(filters, 25, "amount", "asc");
  assert.equal(query.get("sort_by"), "amount");
  assert.equal(query.get("sort_dir"), "asc");
  assert.deepEqual(readTransactionQuery(query), { filters, offset: 25, sortBy: "amount", sortDir: "asc" });
  assert.equal(readTransactionQuery(new URLSearchParams("sort_by=invalid&sort_dir=sideways")).sortBy, "occurred_at");
});
