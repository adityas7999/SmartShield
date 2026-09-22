import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
const liveDescribe =
  process.env.SMARTSHIELD_LIVE_API === "1" ? describe : describe.skip;
const nativeFetch = globalThis.fetch;
const base = "http://127.0.0.1:8000";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
liveDescribe("real React → Python → solc → C++ acceptance", () => {
  it("preserves every multi-anomaly finding, evidence and remediation; supports filters and shared lines", async () => {
    let report;
    vi.stubGlobal("fetch", async (input, init) => {
      const response = await nativeFetch(new URL(String(input), base), init);
      if (String(input).endsWith("/api/analyze"))
        report = await response.clone().json();
      return response;
    });
    render(<App />);
    fireEvent.click(
      screen.getByRole("button", { name: "Multi-anomaly sample" }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Solidity source code").value).toContain(
        "contract Multi",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
    await screen.findByText("4 findings", {}, { timeout: 15000 });
    expect(report.findings).toHaveLength(4);
    const list = screen.getByRole("navigation", { name: "Findings" });
    expect(within(list).getAllByRole("button")).toHaveLength(
      report.findings.length,
    );
    for (const finding of report.findings) {
      fireEvent.click(list.querySelector(`[data-finding-id="${finding.id}"]`));
      const detail = screen.getAllByRole("article", {
        name: `Details ${finding.id}`,
      })[0];
      expect(within(detail).getByText(finding.explanation)).toBeInTheDocument();
      expect(within(detail).getByText(finding.remediation)).toBeInTheDocument();
      for (const evidence of finding.evidence)
        expect(detail.textContent).toContain(evidence.description);
      expect(detail.textContent).toContain(`${finding.confidence} confidence`);
    }
    expect(
      screen.getAllByRole("button", { name: /Select .* on line \d+/ }),
    ).toHaveLength(4);
    fireEvent.change(screen.getByLabelText("Rule"), {
      target: { value: "REN-001" },
    });
    expect(within(list).getAllByRole("button")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(within(list).getAllByRole("button")).toHaveLength(4);
  }, 20000);
  it("renders every rule acceptance response and preserves coverage", async () => {
    vi.stubGlobal("fetch", (input, init) =>
      nativeFetch(new URL(String(input), base), init),
    );
    const rows = JSON.parse(
      readFileSync(resolve(process.cwd(), "../tests/acceptance/manifest.json")),
    );
    for (const row of rows) {
      render(<App />);
      const source = readFileSync(
        resolve(process.cwd(), "../tests/acceptance", row.file),
        "utf8",
      );
      fireEvent.change(screen.getByLabelText("Solidity source code"), {
        target: { value: source },
      });
      fireEvent.change(screen.getByLabelText("File name"), {
        target: { value: row.file },
      });
      fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
      await screen.findByText(
        `Report ready · ${row.unsupported.length ? "partial" : "completed"}`,
        {},
        { timeout: 15000 },
      );
      const expected = Object.values(row.counts).reduce((a, b) => a + b, 0);
      if (expected)
        expect(
          within(
            screen.getByRole("navigation", { name: "Findings" }),
          ).getAllByRole("button"),
        ).toHaveLength(expected);
      else
        expect(
          screen.getByText(/No findings reported. Completed checks:/),
        ).toBeInTheDocument();
      for (const rule of row.unsupported)
        expect(screen.getByText(rule).parentElement.textContent).toContain(
          "unsupported",
        );
      cleanup();
    }
  }, 180000);
});
