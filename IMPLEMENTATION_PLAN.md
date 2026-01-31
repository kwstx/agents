# AGENT FORGE: IMPLEMENTATION PLAN
## "The Black Box Flight Recorder for Autonomous Systems"

**Mission**: Transform Agent Forge from a cloud-ready simulator into a local-first, forensic-grade liability capture system that runs inside the customer's perimeter.

**Core Positioning**: "We run where the risk lives. The truth never leaves."

---

## STRATEGIC PILLARS

### 1. Local-First Architecture
- All data stays on customer infrastructure by default
- No cloud dependencies for core functionality
- Explicit, auditable exports only
- Zero-trust security model

### 2. The PIRD (Pre-Incident Risk Dossier) as Center of Gravity
- Permanent, submittable artifact for legal/insurance use
- Proves preventability, not just detection
- Survives humans, outlasts software

### 3. Business Truth Layer (Ontology)
- Move from technical logs to liability-focused entities
- Agent, Asset, Goal, GovernanceStandard as first-class objects
- Enable fault attribution and impact analysis

### 4. Forensic-Grade Evidence
- Immutable, tamper-proof logs
- Hash-chained audit trails
- Cryptographic verification of data integrity

---

## PHASE 1: SEALED SYSTEM FOUNDATION (Week 1-2)

### Objective
Eliminate cloud dependencies and establish local-first trust signals.

### 1.1 Network Isolation
**Files**: `src/agent_forge/api/server.py`, CLI entry points

**Actions**:
- Bind FastAPI server to `127.0.0.1` only (never `0.0.0.0`)
- Add `--offline` flag to all CLI commands (default: ON)
- Implement network call blocker that prevents any outbound connections in offline mode
- Add startup banner: "Agent Forge is running in sealed mode. No external connections."

**Acceptance Criteria**:
- Running `netstat` shows only localhost bindings
- No DNS queries or HTTP requests in offline mode
- Clear visual confirmation of sealed operation

### 1.2 Immutable Justice Log
**Files**: `utils/interaction_logger.py`, new `src/agent_forge/core/evidence.py`

**Actions**:
- Implement hash-chained logging (each entry references hash of previous entry)
- Add cryptographic signatures to log entries (timestamp + data hash)
- Create write-once directory structure with restrictive permissions
- Build `verify-logs` command to check integrity of entire log chain

**Data Structure**:
```python
{
  "entry_id": "uuid",
  "timestamp": "iso8601",
  "previous_hash": "sha256",
  "data": {...},
  "signature": "sha256(timestamp + data + previous_hash)"
}
```

**Acceptance Criteria**:
- Any log modification breaks the hash chain
- `agent-forge verify-logs` detects tampering
- Logs are append-only at filesystem level

### 1.3 Export Audit Trail
**Files**: New `src/agent_forge/core/export_audit.py`

**Actions**:
- Create `export_audit.log` that records all data exports
- Log: timestamp, user, command, output path, data hash
- Make audit log itself hash-chained and immutable
- Add `--audit-trail` flag to view export history

**Acceptance Criteria**:
- Every PIRD export is logged
- Audit trail cannot be disabled
- Trail is human-readable and machine-parseable

---

## PHASE 2: BUSINESS TRUTH LAYER (Week 2-3)

### Objective
Implement the Ontology that translates technical events into liability-focused entities.

### 2.1 Core Ontology Classes
**Files**: `src/agent_forge/core/ontology.py`

**Actions**:
- Implement `Agent` (liable actor: id, type, version, metadata)
- Implement `Asset` (exposed value: id, type, valuation_usd)
- Implement `Goal` (contractual objective: id, description, criticality, impact_description)
- Implement `GovernanceStandard` (rulebook: name, version, rules)
- Implement `EvidenceAnchor` (technical signal: timestamp, signal_type, measured_value, unit, confidence_interval)
- Implement `FaultType` enum (LOGIC_DEFECT, ENVIRONMENTAL_STRESS, RESOURCE_EXHAUSTION, GOVERNANCE_BREACH, UNDETERMINED)

**Acceptance Criteria**:
- All classes are dataclasses with type hints
- Clear separation between technical data and business semantics
- No business logic in ontology classes (pure data structures)

### 2.2 Upgrade RiskMonitor with Evidence Anchors
**Files**: `src/agent_forge/core/risk.py`

**Actions**:
- Add `evidence_anchors` field to risk events
- Capture lossless technical signals (latency, memory delta, battery level)
- Associate violations with specific GovernanceStandard rules
- Add confidence intervals to all measurements

**Acceptance Criteria**:
- Every risk event has at least one evidence anchor
- Evidence is machine-readable and human-interpretable
- No data loss in translation from raw metrics to risk events

### 2.3 Environment Ontology Mapping
**Files**: `src/agent_forge/envs/warehouse.py`, `src/agent_forge/envs/finance.py`

**Actions**:
- Map WarehouseEnv state to Ontology objects (Robot → Agent, Inventory → Asset, Delivery → Goal)
- Map OrderBookEnv state to Ontology objects (TradingBot → Agent, Portfolio → Asset, ProfitTarget → Goal)
- Define default GovernanceStandards for each environment
- Create factory methods: `env.to_ontology()` → returns (agents, assets, goals, standard)

**Acceptance Criteria**:
- Every environment can export its state as Ontology objects
- Ontology is environment-agnostic (same structure for Warehouse and Finance)
- Clear mapping documentation for each environment

---

## PHASE 3: THE DOSSIER ENGINE (Week 3-4)

### Objective
Build the Legal Translation Layer that generates the PIRD artifact.

### 3.1 DossierGenerator Core
**Files**: `src/agent_forge/forensics/dossier.py`

**Actions**:
- Implement `DossierGenerator(agent, assets, goals, standard)`
- Build `process_technical_event(event)` → converts RiskEvent to Incident
- Implement fault attribution logic:
  - If `is_latency_correlated` → ENVIRONMENTAL_STRESS (preventability: 0.95)
  - If critical failure without stress → LOGIC_DEFECT (preventability: 0.40)
  - If policy breach → GOVERNANCE_BREACH (preventability: 0.80)
- Calculate liability exposure: `(impact_score / 100) * (total_asset_value * risk_multiplier)`
- Build preventability narrative generator (conservative, versioned claims)

**Acceptance Criteria**:
- Every incident has fault attribution, liability estimate, preventability score
- Narratives use conservative language ("demonstrably preventable under these assumptions")
- All claims are versioned and include confidence bounds

### 3.2 PIRD Export Formats
**Files**: `src/agent_forge/forensics/dossier.py`, `src/agent_forge/cli/export.py`

**Actions**:
- Implement `generate_pird()` → returns formatted text report
- Implement `export_json(path)` → machine-readable PIRD
- Implement `export_pdf(path)` → using reportlab or similar
- Add redaction tool: `redact_pird(fields_to_remove)` for sanitization
- Add signing: `sign_pird(private_key)` for authenticity verification

**PIRD Structure**:
```
[1.0] EXECUTIVE SUMMARY
  - Status (COMPLIANT / CRITICAL_VIOLATION)
  - Primary Agent
  - Total Preventable Incidents
  
[2.0] ASSET EXPOSURE & OBJECTIVES
  - List of Assets with valuations
  - List of Goals with criticality
  
[3.0] ANALYTICAL FINDINGS
  - For each incident:
    - Incident ID
    - Fault Attribution
    - Estimated Liability Exposure (USD)
    - Preventability Score (0-100%)
    - Forensic Narrative
    - Technical Evidence Anchors
    
[4.0] GOVERNANCE COMPLIANCE
  - GovernanceStandard applied
  - Rules tested
  - Violations detected
```

**Acceptance Criteria**:
- PIRD is human-readable (executive can understand in 2 minutes)
- PIRD is machine-parseable (can be ingested by compliance systems)
- PIRD can be exported, signed, and verified independently

### 3.3 CLI Export Commands
**Files**: `src/agent_forge/cli/export.py`

**Actions**:
- `agent-forge export-pird --output /path/report.txt` (text format)
- `agent-forge export-pird --output /path/report.json` (JSON format)
- `agent-forge export-pird --output /path/report.pdf --sign-with-key /path/key.pem`
- `agent-forge redact-pird --input /path/report.json --remove-fields agent.metadata --output /path/redacted.json`
- `agent-forge verify-pird --input /path/report.json --public-key /path/key.pub`

**Acceptance Criteria**:
- All exports are logged to audit trail
- Signing/verification uses standard cryptographic libraries
- Redaction is irreversible (no recovery of removed fields)

---

## PHASE 4: POST-MORTEM REPLAY (Week 4-5)

### Objective
Prove the "Offline Shadow Mode" value proposition: analyze historical logs to generate retrospective PIRDs.

### 4.1 Log Replay Engine
**Files**: `src/agent_forge/forensics/replay.py`

**Actions**:
- Build `LogReplayer(log_file)` that reads `simulation_events.jsonl`
- Reconstruct simulation state from historical logs
- Re-run RiskMonitor and ComplianceAuditor on historical data
- Generate PIRD from replayed events

**CLI**:
```bash
agent-forge replay --logs /path/simulation_events.jsonl --output /path/pird.txt
```

**Acceptance Criteria**:
- Can replay any historical log file
- PIRD generated from replay matches live simulation results
- No network access required for replay

### 4.2 Golden Failure Validation
**Files**: `tests/test_pird_generation.py`

**Actions**:
- Run `test_golden_failures.py` scenarios
- Verify each scenario generates a PIRD
- Assert preventability scores:
  - Causal Battery Death (environmental stress) → 0.95
  - Risk Escalation (logic defect) → 0.40
  - Agent Isolation (governance breach) → 0.80
- Verify fault attribution is correct for each scenario

**Acceptance Criteria**:
- All golden failures produce valid PIRDs
- Preventability scores are conservative and accurate
- Fault attribution matches expected root cause

---

## PHASE 5: TERMINAL-FIRST INTERFACE (Week 5-6)

### Objective
Replace web dashboard with a sealed, local-first user interface.

### 5.1 Terminal UI (TUI)
**Files**: `src/agent_forge/ui/tui.py`

**Actions**:
- Build TUI using `rich` or `textual` library
- Screens:
  - **Dashboard**: Current simulation status, risk scores, active agents
  - **Incident Log**: List of all detected incidents with fault attribution
  - **Lineage Graph**: Agent → Asset → Goal → Violation relationships
  - **Export**: PIRD generation and export interface
- Add keyboard shortcuts (no mouse required)
- Add `agent-forge tui` command to launch interface

**Acceptance Criteria**:
- TUI runs in any terminal (no GUI dependencies)
- All core functionality accessible via TUI
- No network calls from TUI

### 5.2 Localhost Web UI (Optional)
**Files**: `src/agent_forge/api/server.py`, `ui/` directory

**Actions**:
- Make web UI opt-in: `agent-forge serve --enable-web-ui --i-understand-this-opens-a-port`
- Bind to `127.0.0.1` only (never `0.0.0.0`)
- Add warning banner: "Web UI is enabled. This opens a local port. Use TUI for maximum security."
- Simplify UI to "Dossier Viewer" (remove real-time features)
- Primary CTA: "Download PIRD"

**Acceptance Criteria**:
- Web UI is disabled by default
- Requires explicit flag to enable
- Clear security warnings when enabled

### 5.3 UI Aesthetic Pivot
**Files**: All UI components

**Actions**:
- Remove "cool" graphics, animations, gradients
- Adopt "Bloomberg Terminal" aesthetic: high-density tables, monochrome risk indicators
- Focus on data density over visual appeal
- Use monospace fonts, clear hierarchies, minimal color (red for critical, yellow for warning, green for compliant)

**Acceptance Criteria**:
- UI looks "serious" and "professional"
- No wasted screen space
- Executives can understand at a glance

---

## PHASE 6: ENTERPRISE HARDENING (Week 6-8)

### Objective
Prepare for on-prem deployment in regulated environments.

### 6.1 Offline Licensing
**Files**: `src/agent_forge/licensing/`

**Actions**:
- Implement offline license key system (signed JWTs)
- `agent-forge activate --license-file /path/license.key`
- Support air-gapped licensing:
  - Customer generates machine fingerprint: `agent-forge fingerprint > machine.txt`
  - Customer sends fingerprint to vendor
  - Vendor generates signed license file
  - Customer activates: `agent-forge activate --license-file license.key`
- License validation is local (no phone-home)

**Acceptance Criteria**:
- No network required for license validation
- License tampering is detectable
- Clear error messages for invalid/expired licenses

### 6.2 Deterministic Builds
**Files**: Build scripts, `pyproject.toml`

**Actions**:
- Pin all dependencies to exact versions
- Use `pip-tools` or `poetry` for reproducible builds
- Generate SBOM (Software Bill of Materials)
- Provide checksums for all release artifacts
- Document build process for customer verification

**Acceptance Criteria**:
- Same source code produces identical binaries
- Customers can verify build integrity
- No hidden dependencies or telemetry

### 6.3 Air-Gapped Deployment Support
**Files**: Deployment documentation, install scripts

**Actions**:
- Create "offline install bundle" with all dependencies
- Document manual installation process
- Provide update bundles (no internet required)
- Support manual license activation
- Test installation on isolated VM

**Acceptance Criteria**:
- Can install on machine with no internet
- All dependencies included in bundle
- Clear documentation for IT teams

---

## PHASE 7: DOCUMENTATION & POSITIONING (Week 8-9)

### Objective
Align all external communication with "local-first, forensic-grade" positioning.

### 7.1 Product Documentation
**Files**: `docs/` directory

**Actions**:
- Write "Black Box Flight Recorder" positioning doc
- Create "Zero Trust Architecture" technical whitepaper
- Document PIRD format specification
- Write "Insurance Submission Guide" for customers
- Create "Air-Gapped Deployment Guide"

**Acceptance Criteria**:
- Non-technical executives can understand value proposition
- Technical teams can deploy without vendor support
- Clear differentiation from cloud-based tools

### 7.2 Security & Compliance Documentation
**Files**: `docs/security/`, `docs/compliance/`

**Actions**:
- Document data flow (all local, no external calls)
- Create "Audit Trail Specification"
- Write "Cryptographic Verification Guide"
- Document "PIRD as Legal Evidence" best practices
- Create "GDPR/SOC2 Compliance" statement

**Acceptance Criteria**:
- Customers can pass security reviews
- Clear answers to "where does data go?"
- Compliance teams can approve deployment

### 7.3 Positioning Messaging
**Files**: README.md, website copy, pitch deck

**Actions**:
- Update all messaging to emphasize local-first
- Remove cloud/SaaS language
- Add "runs inside your perimeter" messaging
- Emphasize "the truth never leaves"
- Compare to Bloomberg Terminal, Palantir on-prem

**Key Messages**:
- "The black box flight recorder for autonomous systems"
- "We run where the risk lives"
- "Forensic-grade evidence that never leaves your control"
- "Post-incident survival, not failure prevention"
- "Proving preventability, not predicting success"

**Acceptance Criteria**:
- Clear differentiation from cloud tools
- Messaging resonates with CROs and compliance officers
- No confusion about deployment model

---

## SUCCESS METRICS

### Technical Metrics
- [ ] All network calls blocked in offline mode
- [ ] Hash chain integrity verified on 10,000+ log entries
- [ ] PIRD generation time < 5 seconds for 1,000 events
- [ ] TUI runs on Windows, macOS, Linux
- [ ] Air-gapped install successful on isolated VM

### Business Metrics
- [ ] Customer can submit PIRD to insurer without modification
- [ ] Risk officer understands fault attribution in < 2 minutes
- [ ] Security team approves deployment without vendor access
- [ ] PIRD accepted as evidence in compliance audit
- [ ] Customer renews because "we can't operate without the audit trail"

### Positioning Metrics
- [ ] Prospects ask "is this like Palantir?" (yes)
- [ ] Prospects ask "does this run in the cloud?" (no, and that's the point)
- [ ] Buyers are CROs/compliance, not just ML engineers
- [ ] Deals close on "liability protection," not "better testing"

---

## ANTI-ROADMAP (What NOT to Build)

### Do NOT Build:
- ❌ Multi-tenant SaaS platform
- ❌ Cloud-based license server
- ❌ Telemetry or analytics (unless explicit opt-in)
- ❌ "Sign up online" flow
- ❌ Real-time collaboration features
- ❌ Mobile app
- ❌ Browser extensions
- ❌ Third-party integrations that require API keys
- ❌ "Helpful" features that phone home

### Why:
These features undermine the "sealed system" trust model. If you build them, you become a cloud tool. Cloud tools cannot sell to compliance officers.

---

## EXECUTION DISCIPLINE

### Weekly Checkpoints
- Every Friday: Review progress against phase objectives
- Ask: "Does this feature serve the PIRD?"
- Ask: "Does this feature require network access?"
- If yes to #2, reject unless absolutely necessary

### Decision Framework
For every feature request, ask:
1. Does this make the PIRD more credible in court?
2. Does this maintain the sealed system trust model?
3. Does this help customers survive post-incident audits?

If not all three, defer or reject.

---

## FINAL POSITIONING STATEMENT

**Agent Forge is the black box flight recorder for autonomous systems.**

We don't predict success. We prove preventability.

We don't run in the cloud. We run where the risk lives.

We don't store your data. You do.

When your autonomous system fails—and it will—you will not be blind.

The truth stays with you. Forever.
