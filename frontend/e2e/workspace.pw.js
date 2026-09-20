import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test("real multi-rule report, source navigation, export, print, and coverage", async ({
  page,
}, info) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Multi-anomaly sample" }).click();
  await expect(page.getByLabel("Solidity source code")).toContainText(
    /contract\s+\w+/,
  );
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/analyze"),
  );
  await page
    .getByRole("button", { name: "Analyze contract", exact: true })
    .click();
  const report = await (await response).json();
  expect(report.findings).toHaveLength(4);
  await expect(
    page.getByRole("heading", { name: "4 findings", exact: true }),
  ).toBeVisible();
  const list = page.getByRole("navigation", { name: "Findings", exact: true });
  await expect(list.getByRole("button")).toHaveCount(4);
  for (const f of report.findings) {
    await list.locator(`[data-finding-id="${f.id}"]`).click();
    const detail = page
      .locator(".findings-workspace")
      .getByRole("article", { name: `Details ${f.id}`, exact: true });
    await expect(detail).toContainText(f.remediation);
    for (const e of f.evidence)
      await expect(detail).toContainText(e.description);
    await detail.getByRole("button").first().click();
    await expect(page.locator(".code-line.focused").first()).toBeVisible();
  }
  await expect(
    page.getByRole("button", { name: /Select .* on line 3/ }),
  ).toHaveCount(4);
  await page.getByLabel("Rule", { exact: true }).selectOption("UEC-001");
  await expect(list.getByRole("button")).toHaveCount(1);
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download JSON" }).click();
  const download = await downloadEvent;
  expect(JSON.parse(readFileSync(await download.path(), "utf8"))).toEqual(
    report,
  );
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".print-findings article")).toHaveCount(4);
  for (const article of await page.locator(".print-findings article").all())
    await expect(article).toBeVisible();
  await page.emulateMedia({ media: "screen" });
  await page.getByRole("button", { name: "Clear filters" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `../build/workspace-${info.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Unsupported sample" }).click();
  await expect(page.getByLabel("Solidity source code")).toContainText(
    "modifier auth",
  );
  await page
    .getByRole("button", { name: "Analyze contract", exact: true })
    .click();
  await expect(page.getByText("Report ready · partial")).toBeVisible();
  await expect(
    page.getByText("No findings reported. Completed checks: none.", {
      exact: false,
    }),
  ).toBeVisible();
});

test("compiler and actual analyzer failure recover to completed no-finding report", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Solidity source code").fill("contract Broken {");
  await page
    .getByRole("button", { name: "Analyze contract", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Compilation failed" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "No-finding sample" }).click();
  await expect(page.getByLabel("Solidity source code")).toContainText(
    "msg.sender",
  );
  await page.route("**/api/analyze", async (route) => {
    const response = await page.request.post(
      "http://127.0.0.1:8001/api/analyze",
      { data: route.request().postDataJSON() },
    );
    await route.fulfill({ response });
  });
  await page
    .getByRole("button", { name: "Analyze contract", exact: true })
    .click();
  await expect(
    page.getByText("analyzer_unavailable", { exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/analyze");
  await page
    .getByRole("button", { name: "Analyze contract", exact: true })
    .click();
  await expect(page.getByText("Report ready · completed")).toBeVisible();
  await expect(
    page.getByText(
      /No findings reported. Completed checks: TXO-001, REN-001, ACC-001, UEC-001/,
    ),
  ).toBeVisible();
});
