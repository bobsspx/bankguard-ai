import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

type Fixture = { email: string; password: string; account_ref: string; case_id: string };

test("synthetic banking smoke through the local API", async ({ page }, testInfo) => {
  const fixtureFile = process.env.CI_BROWSER_AUTH_FILE;
  if (!fixtureFile) throw new Error("Isolated CI browser fixture required");
  const fixture = JSON.parse(readFileSync(fixtureFile, "utf8")) as Fixture;

  await page.goto("/login");
  await page.getByLabel("Email").fill(fixture.email);
  await page.getByLabel("Password").fill(fixture.password);
  const loginResponse = page.waitForResponse(response => response.url().endsWith("/api/auth/login"));
  await page.getByRole("button", { name: "Sign in" }).click();
  expect((await loginResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Transaction Monitoring" })).toBeVisible();
  const me = await page.request.get("/api/auth/me");
  expect(me.status()).toBe(200);
  expect((await me.json()).role).toBe("fraud_analyst");

  await page.getByPlaceholder("Account ref").fill(fixture.account_ref);
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.locator('section[aria-label="Transaction summary"] strong').first()).toHaveText("30");
  await page.locator("#transactionSortBy").selectOption("amount");
  await page.locator("#transactionSortDir").selectOption("asc");
  await expect(page.locator('th[aria-sort="ascending"]')).toContainText("AMOUNT");
  await expect(page.locator("table tbody tr td:nth-child(3) strong").first()).toContainText("1.00");
  await expect(page.locator("table tbody tr")).toHaveCount(25);
  const amounts = await page.locator("table tbody tr td:nth-child(3) strong").allTextContents();
  expect(amounts.map(value => Number.parseFloat(value))).toEqual(Array.from({ length: 25 }, (_, index) => index + 1));

  await page.locator('#transactionSortDir').selectOption('desc');
  await expect(page.locator('th[aria-sort="descending"]')).toContainText('AMOUNT');
  await expect(page.locator("table tbody tr td:nth-child(3) strong").first()).toContainText("30.00");
  await page.screenshot({ path: testInfo.outputPath("monitoring.png") });
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page).toHaveURL(/offset=25.*sort_by=amount.*sort_dir=desc/);
  await page.locator("table tbody tr").first().getByRole("link", { name: "View details" }).click();
  await expect(page.getByRole("heading", { name: "Transaction Detail" })).toBeVisible();
  await page.getByRole("link", { name: /Transaction Monitoring/ }).click();
  await expect(page).toHaveURL(/offset=25.*sort_by=amount.*sort_dir=desc/);

  await page.goto(`/cases?caseId=${fixture.case_id}`);
  await expect(page.getByRole("heading", { name: "Evidence and audit" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Audit history" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("case-context.png") });
  expect((await page.request.get("/api/security/summary")).status()).toBe(403);
  await expect(page.getByRole("link", { name: "Security Operations" })).toHaveCount(0);
  if (page.viewportSize()?.width === 390) {
    await page.getByRole("button", { name: "Toggle navigation" }).click();
    await expect(page.getByRole("button", { name: "Toggle navigation" })).toHaveAttribute("aria-expanded", "true");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  }

  const logoutResponse = page.waitForResponse(response => response.url().endsWith("/api/auth/logout"));
  await page.getByRole("button", { name: "Sign out" }).click();
  expect((await logoutResponse).status()).toBe(200);
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get("/api/auth/me")).status()).toBe(401);
  expect((await page.request.get("/api/cases")).status()).toBe(401);
});
