import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Opt-in browser smoke + automated accessibility (axe). Stable + graceful:
 * seeded-data steps skip when no project exists. Axe fails only on
 * serious/critical violations.
 */

async function axeSerious(page: Page): Promise<{ id: string; impact: string }[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => ({ id: v.id, impact: v.impact ?? "" }));
}

/** Returns a seeded project id (from the Project List) or null. */
async function firstProjectId(page: Page): Promise<string | null> {
  await page.goto("/");
  const row = page.locator("button:has-text('created')").first();
  if (!(await row.isVisible().catch(() => false))) return null;
  await row.click();
  await page.waitForURL(/\/projects\/[^/]+\/workflow/, { timeout: 10_000 }).catch(() => {});
  const m = page.url().match(/\/projects\/([^/]+)\//);
  return m ? m[1] : null;
}

// --- shell + navigation -----------------------------------------------------

test("app shell + primary navigation render", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("FMCG Innovation Reaction Simulator")).toBeVisible();
  await expect(page.getByRole("link", { name: "Projects" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Portfolio" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Compare" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Skip to content/i })).toBeAttached();
});

test("portfolio and compare routes load", async ({ page }) => {
  await page.goto("/portfolio");
  await expect(page.getByRole("heading", { name: /Innovation portfolio/i })).toBeVisible();
  await page.goto("/compare");
  await expect(page.getByRole("heading", { name: /Compare concepts/i })).toBeVisible();
});

test("glossary opens and closes (Escape)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /^Glossary$/ }).click();
  await expect(page.getByRole("dialog", { name: /Glossary/i })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: /Glossary/i })).toBeHidden();
});

// --- seeded flow (best-effort) ---------------------------------------------

test("seeded project pages load", async ({ page }) => {
  const pid = await firstProjectId(page);
  test.skip(!pid, "No seeded project — run scripts/seed_demo.py to enable this flow.");
  await page.goto(`/projects/${pid}/home`);
  await expect(page.getByText(/What to do next/i)).toBeVisible({ timeout: 10_000 });
  await page.goto(`/projects/${pid}/studio`);
  await expect(page.getByRole("heading", { name: /Agent Studio/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Live Mode/i })).toBeVisible();
  await page.goto(`/projects/${pid}/events`);
  await expect(page.getByText(/Event explorer/i)).toBeVisible();
  await page.goto(`/projects/${pid}/report`);
  // report may 409 before generation; accept either the report or a friendly error
  await expect(page.getByText(/Strategic launch report|Generate the strategic report/i)).toBeVisible({ timeout: 10_000 });
});

// --- accessibility (axe) ----------------------------------------------------

test("a11y: app shell has no serious/critical axe violations", async ({ page }) => {
  await page.goto("/");
  expect(await axeSerious(page)).toEqual([]);
});

test("a11y: portfolio has no serious/critical axe violations", async ({ page }) => {
  await page.goto("/portfolio");
  expect(await axeSerious(page)).toEqual([]);
});

test("a11y: open glossary dialog has no serious/critical axe violations", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /^Glossary$/ }).click();
  await expect(page.getByRole("dialog", { name: /Glossary/i })).toBeVisible();
  expect(await axeSerious(page)).toEqual([]);
});

test("a11y: seeded Home + Studio (best-effort)", async ({ page }) => {
  const pid = await firstProjectId(page);
  test.skip(!pid, "No seeded project — run scripts/seed_demo.py to enable this flow.");
  await page.goto(`/projects/${pid}/home`);
  await expect(page.getByText(/What to do next/i)).toBeVisible({ timeout: 10_000 });
  expect(await axeSerious(page)).toEqual([]);
  await page.goto(`/projects/${pid}/studio`);
  await expect(page.getByRole("heading", { name: /Agent Studio/i })).toBeVisible();
  expect(await axeSerious(page)).toEqual([]);
});
