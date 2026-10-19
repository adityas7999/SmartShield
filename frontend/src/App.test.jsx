import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App.jsx";
const rules = ["TXO-001", "REN-001", "ACC-001", "UEC-001", "TMP-001"];
const report = {
  schemaVersion: "1.0.0",
  reportVersion: "1.0.0",
  status: "completed",
  source: { fileName: "Contract.sol" },
  ruleResults: rules.map((ruleId) => ({
    ruleId,
    status: "completed",
    reasons: [],
  })),
  findings: [],
  summary: {
    total: 0,
    byRule: Object.fromEntries(rules.map((r) => [r, 0])),
    bySeverity: { high: 0, medium: 0, low: 0 },
  },
  analysisLimitations: ["Zero findings is not a security guarantee."],
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
it("reports exact completed coverage for empty results", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(report))),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  expect(
    await screen.findByText(
      /No findings reported. Completed checks: TXO-001, REN-001, ACC-001, UEC-001, TMP-001/,
    ),
  ).toBeInTheDocument();
});
it("shows compiler diagnostics and recovers with another submission", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: {
              code: "parse_failed",
              message: "Solidity compilation failed.",
              diagnostics: ["ParserError"],
              report: {
                ...report,
                status: "compilation_error",
                ruleResults: rules.map((ruleId) => ({
                  ruleId,
                  status: "failed",
                  reasons: ["Compiler failed"],
                })),
              },
            },
          }),
          { status: 422 },
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(report))),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  expect(
    await screen.findByRole("heading", { name: "Compilation failed" }),
  ).toBeInTheDocument();
  expect(screen.getByText("ParserError")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  expect(await screen.findByText(/No findings reported/)).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
it("shows analyzer errors separately", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: { code: "analyzer_failure", message: "Engine failed" },
          }),
          { status: 502 },
        ),
      ),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  expect(await screen.findByText("Engine failed")).toBeInTheDocument();
  expect(screen.queryByText(/No findings reported/)).not.toBeInTheDocument();
});
it("keeps all same-line occurrences and prints all findings despite filters", async () => {
  const span = {
    available: true,
    file: "Contract.sol",
    line: 4,
    endLine: 4,
    column: 1,
    endColumn: 2,
    offset: 1,
    length: 1,
  };
  const findings = ["a", "b", "c"].map((id, i) => ({
    id,
    ruleId: i === 2 ? "TXO-001" : "UEC-001",
    title: `Finding ${id}`,
    severity: i === 2 ? "high" : "medium",
    confidence: "high",
    contract: "T",
    function: "f",
    primarySpan: span,
    evidence: [{ description: `Evidence ${id}`, span }],
    explanation: `Reason ${id}`,
    remediation: `Fix ${id}`,
    limitations: ["Bounded"],
  }));
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            ...report,
            findings,
            summary: { ...report.summary, total: 3 },
          }),
        ),
      ),
  );
  const print = vi.spyOn(window, "print").mockImplementation(() => {});
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  await screen.findByText("3 findings");
  expect(
    screen.getAllByRole("button", { name: /Select .* on line 4/ }),
  ).toHaveLength(3);
  fireEvent.change(screen.getByLabelText("Rule"), {
    target: { value: "UEC-001" },
  });
  expect(
    within(screen.getByRole("navigation", { name: "Findings" })).getAllByRole(
      "button",
    ),
  ).toHaveLength(2);
  expect(document.querySelectorAll(".print-findings article")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "Print report" }));
  expect(print).toHaveBeenCalledOnce();
});
it("invalidates the report when source identity changes", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(report))),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  await screen.findByText(/No findings reported/);
  fireEvent.change(screen.getByLabelText("File name"), {
    target: { value: "Other.sol" },
  });
  expect(
    screen.queryByRole("region", { name: "Analysis report" }),
  ).not.toBeInTheDocument();
});

it("generates verified candidate remediation and displays unified diff", async () => {
  const span = {
    available: true,
    file: "Contract.sol",
    line: 4,
    endLine: 4,
    column: 1,
    endColumn: 2,
    offset: 1,
    length: 1,
  };
  const finding = {
    id: "TXO-1",
    ruleId: "TXO-001",
    title: "Transaction origin used for authorization",
    severity: "high",
    confidence: "high",
    contract: "Vault",
    function: "withdraw",
    primarySpan: span,
    evidence: [{ description: "Origin identity used", span }],
    explanation: "tx.origin used in require",
    remediation: "Use msg.sender instead",
    limitations: ["Bounded"],
  };

  const reportWithFinding = {
    ...report,
    findings: [finding],
    summary: { ...report.summary, total: 1, byRule: { ...report.summary.byRule, "TXO-001": 1 } },
  };

  const remediationResponse = {
    status: "verified",
    findingId: "TXO-1",
    ruleId: "TXO-001",
    explanation: "Replaced tx.origin with msg.sender.",
    originalSource: "require(tx.origin == owner);",
    patchedSource: "require(msg.sender == owner);",
    diff: "--- a/Contract.sol\n+++ b/Contract.sol\n- require(tx.origin == owner);\n+ require(msg.sender == owner);",
    compilationPassed: true,
    targetEliminated: true,
    remainingFindingsCount: 0,
    reverified: true,
  };

  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (url) => {
      if (String(url).endsWith("/api/remediate")) {
        return new Response(JSON.stringify(remediationResponse));
      }
      return new Response(JSON.stringify(reportWithFinding));
    }),
  );

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze contract" }));
  await screen.findByText("1 finding");

  const generateBtn = await screen.findByRole("button", { name: "⚡ Generate Verified Fix" });
  expect(generateBtn).toBeInTheDocument();

  fireEvent.click(generateBtn);
  expect(await screen.findByText(/Re-compiled & Verified/)).toBeInTheDocument();
  expect(screen.getByText("Unified Git Diff")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Apply Fix to Editor/ })).toBeInTheDocument();
});
