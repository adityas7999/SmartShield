"""One validated report contract shared by the API, schema file, and frontend."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

RULES = ('TXO-001', 'REN-001', 'ACC-001', 'UEC-001')
Rule = Literal['TXO-001', 'REN-001', 'ACC-001', 'UEC-001']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Span(Strict):
    file: str
    offset: int = Field(ge=0)
    length: int = Field(ge=0)
    line: int = Field(ge=1)
    column: int = Field(ge=1)
    endLine: int = Field(ge=1)
    endColumn: int = Field(ge=1)
    available: bool

class Evidence(Strict):
    description: str
    span: Span | None = None

class Finding(Strict):
    id: str
    ruleId: Rule
    title: str
    severity: Literal['high', 'medium', 'low']
    confidence: Literal['high', 'medium', 'low']
    contract: str
    function: str
    primarySpan: Span
    evidence: list[Evidence] = Field(min_length=1)
    explanation: str
    limitations: list[str]
    remediation: str

class RuleResult(Strict):
    ruleId: Rule
    status: Literal['completed', 'unsupported', 'failed']
    reasons: list[str]

class Source(Strict):
    fileName: str
    byteLength: int = Field(ge=0)
    sha256: str | None = None

class Summary(Strict):
    total: int
    byRule: dict[Rule, int]
    bySeverity: dict[Literal['high', 'medium', 'low'], int]

class Report(Strict):
    schemaVersion: Literal['1.0.0']
    reportVersion: Literal['1.0.0']
    status: Literal['completed', 'partial', 'compilation_error', 'analyzer_error']
    source: Source
    compilerVersion: str | None = None
    compilerErrors: list[str]
    ruleResults: list[RuleResult]
    findings: list[Finding]
    summary: Summary
    analysisLimitations: list[str]

    @model_validator(mode='after')
    def consistency(self):
        assert sorted(r.ruleId for r in self.ruleResults) == sorted(RULES), 'exactly four rule statuses required'
        assert len({f.id for f in self.findings}) == len(self.findings), 'duplicate finding IDs'
        assert self.summary.total == len(self.findings), 'total mismatch'
        assert self.summary.byRule == {r: sum(f.ruleId == r for f in self.findings) for r in RULES}, 'rule count mismatch'
        assert self.summary.bySeverity == {s: sum(f.severity == s for f in self.findings) for s in ('high', 'medium', 'low')}, 'severity count mismatch'
        for r in self.ruleResults:
            assert r.status == 'completed' or r.reasons, 'coverage reasons required'
        if self.status == 'completed':
            assert all(r.status == 'completed' for r in self.ruleResults), 'incomplete coverage'
        if self.status == 'partial':
            assert any(r.status == 'unsupported' for r in self.ruleResults), 'partial requires unsupported coverage'
        for f in self.findings:
            for span in [f.primarySpan, *(e.span for e in f.evidence if e.span)]:
                assert span.file == self.source.fileName, 'wrong source identity'
                assert not span.available or span.offset + span.length <= self.source.byteLength, 'invalid source span'
        return self
