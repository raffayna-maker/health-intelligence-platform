# Health Intelligence Platform — Security Architecture

## 1. Platform Overview

The Health Intelligence Platform is a healthcare AI application that provides:
- **Clinical Assistant** — RAG-powered Q&A over patient records
- **Document Processing** — AI-powered extraction and classification of medical documents
- **Research Agent** — Autonomous AI agent that reasons, uses tools, and answers questions
- **Analytics** — Risk scoring, condition analysis, readmission prediction
- **Report Generation** — Security, analytics, and agent reports

All AI interactions are protected by a **defense-in-depth security architecture** using three independent security layers that operate at different points in the request lifecycle.

---

## 2. Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EC2 Instance (Docker)                        │
│                                                                     │
│  ┌──────────┐    ┌────────────┐    ┌──────────────────────────┐    │
│  │  Nginx   │───▶│  Frontend  │    │        Backend           │    │
│  │  :80     │    │  Vite/React│    │     FastAPI :8080        │    │
│  │          │───▶│  :3000     │    │                          │    │
│  │ /api/* ──│────│────────────│───▶│  ┌─────────────────────┐ │    │
│  └──────────┘    └────────────┘    │  │ Security Service    │ │    │
│                                    │  │ (N-Tool Scanner)    │─│─ ─ ─ ─▶ HiddenLayer API
│                                    │  └─────────────────────┘ │    │     PromptFoo API
│                                    │           │              │    │
│                                    │           ▼              │    │
│                                    │  ┌─────────────────────┐ │    │
│                                    │  │ LLM Service         │ │    │
│                                    │  │ (ollama_service.py) │ │    │
│                                    │  └────────┬────────────┘ │    │
│                                    └───────────│──────────────┘    │
│                                                │                   │
│                  ┌─────────────────────────────┼──────────┐       │
│                  │                             │          │       │
│           ┌──────▼─────┐  ┌──────────────┐  ┌─▼────────┐│       │
│           │ PostgreSQL │  │   ChromaDB   │  │ LiteLLM  ││       │
│           │   :5432    │  │    :8000     │  │  :4000   ││       │
│           │  (Main DB) │  │(Vector Store)│  │(LLM Proxy)│       │
│           └────────────┘  └──────────────┘  └─┬────────┘│       │
│                                               │         │       │
│                                    ┌──────────▼───────┐ │       │
│                                    │  AIM Guardrails  │ │       │
│                                    │  (pre_call /     │ │       │
│                                    │   post_call)     │ │       │
│                                    └──────────┬───────┘ │       │
│                                               │         │       │
└───────────────────────────────────────────────│─────────┘       │
                                                │                  │
                                                ▼                  │
                                        ┌──────────────┐          │
                                        │ AWS Bedrock  │          │
                                        │ Claude 3.5   │          │
                                        │ Sonnet       │          │
                                        └──────────────┘          │
```

### Docker Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| **Nginx** | nginx:alpine | 80 | Reverse proxy — routes `/api/*` to backend, `/` to frontend |
| **Frontend** | Custom (Vite/React/TS) | 3000 | Single-page application |
| **Backend** | Custom (FastAPI/Python) | 8080 | API server with all business logic |
| **PostgreSQL** | postgres:16-alpine | 5432 | Main database (patients, security logs, agent runs) |
| **ChromaDB** | chromadb/chroma:0.5.23 | 8000 | Vector store for RAG (200 synthetic patients embedded) |
| **LiteLLM** | ghcr.io/berriai/litellm | 4000 | LLM proxy to AWS Bedrock with AIM guardrails inline |

---

## 3. The Three Security Layers

The platform implements three independent AI security tools, each operating differently:

### Layer 1: AIM Security (Inline via LiteLLM Proxy)

**Type:** Inline guardrails — automatic, no explicit API calls needed

**How it works:**
- AIM is configured as a guardrail within the LiteLLM proxy (`litellm-config.yaml`)
- Every LLM text generation call from the backend goes through LiteLLM
- AIM runs automatically in two modes:
  - **`pre_call`** — Scans the input prompt BEFORE it reaches AWS Bedrock
  - **`post_call`** — Scans the LLM output AFTER Bedrock returns a response
- If AIM blocks, LiteLLM returns HTTP 400 → backend raises `AIMBlockedException`
- If AIM passes, the request/response flows through normally (HTTP 200)

**Configuration** (`litellm-config.yaml`):
```yaml
guardrails:
  - guardrail_name: aim
    litellm_params:
      guardrail: aim
      mode: [pre_call, post_call]
      api_key: <AIM_API_KEY>
      default_on: true
```

**What it scans:** Every `generate()` call — clinical assistant responses, document extractions, agent reasoning, analytics, report generation

**Verdict:** Binary — `pass` (HTTP 200) or `block` (HTTP 400)

**Key characteristic:** AIM is the ONLY security tool that scans LLM outputs inline. It sees both the prompt and the response in context.

---

### Layer 2: HiddenLayer (Explicit API Scanning)

**Type:** Standalone SaaS API — explicit calls made by the backend at specific scan points

**How it works:**
- Backend makes direct HTTP POST requests to HiddenLayer's Prompt Analyzer API
- OAuth2 authentication (client_id/client_secret → bearer token, cached ~54 minutes)
- Supports both input scanning and output scanning
- **Policy-aware**: HiddenLayer detects threats AND checks configured policies to decide whether to block or just alert

**API Endpoint:** `POST https://api.hiddenlayer.ai/api/v1/submit/prompt-analyzer`

**Input scan payload:**
```json
{
  "model": "healthcare-platform",
  "prompt": "<content to scan>"
}
```

**Output scan payload:**
```json
{
  "model": "healthcare-platform",
  "prompt": "<original user prompt>",
  "output": "<LLM response to scan>"
}
```

**Detection categories:**
| Category | Block Policy Flag |
|----------|-------------------|
| `prompt_injection` | `block_prompt_injection` |
| `unsafe_input` | `block_unsafe_input` |
| `unsafe_output` | `block_unsafe_output` |
| `input_pii` | `block_input_pii` |
| `output_pii` | `block_output_pii` |
| `input_code` | `block_input_code_detection` |
| `output_code` | `block_output_code_detection` |
| `input_dos` | `block_input_dos_detection` |
| `guardrail` | `block_guardrail_detection` |

**Verdict logic (policy-aware):**
1. If `verdict: false` → `"pass"` (no threat detected)
2. If `verdict: true` (threat detected):
   - Check which `categories` fired (e.g., `prompt_injection: true`)
   - Check if the corresponding `block_*` policy flag is set to `true`
   - If ANY detected category has its block flag set → `"block"`
   - If NO detected category has its block flag set → `"detected"` (alert only, not blocked)

**Three possible verdicts:** `"pass"`, `"detected"`, `"block"`

**Key characteristic:** HiddenLayer is the only tool with a **three-tier verdict system** (pass/detected/block). Policies are configured in the HiddenLayer console, allowing fine-grained control over what gets blocked vs. just flagged.

---

### Layer 3: PromptFoo (Red Team Scanning + Adaptive Guardrails)

**Type:** Two-phase security — offensive red teaming + defensive guardrails

#### Phase 1: Red Team Scanning (Offensive)

PromptFoo's red team scanner probes the application with adversarial attacks to discover vulnerabilities BEFORE they're exploited in production.

**How it works:**
- The PromptFoo CLI sends 1,330 adversarial test cases directly against the app's `/api/assistant/query` endpoint
- Tests are auto-generated across 38 attack categories + 2 jailbreak strategies
- Each test is evaluated for whether the app's response was safe or unsafe
- Results feed into Adaptive Guardrails (Phase 2)

**Attack categories tested (38 plugins):**
| Category | Tests | Description |
|----------|-------|-------------|
| `bfla` | 5 | Broken Function Level Authorization |
| `bola` | 5 | Broken Object Level Authorization |
| `contracts` | 5 | Terms/contract compliance |
| `excessive-agency` | 5 | AI taking unauthorized actions |
| `hallucination` | 5 | AI fabricating information |
| `harmful:chemical-biological-weapons` | 5 | WMD-related content |
| `harmful:child-exploitation` | 5 | CSAM content |
| `harmful:copyright-violations` | 5 | IP theft |
| `harmful:cybercrime` | 5 | Hacking/fraud assistance |
| `harmful:cybercrime:malicious-code` | 5 | Malware generation |
| `harmful:graphic-content` | 5 | Gore/violence |
| `harmful:harassment-bullying` | 5 | Targeted harassment |
| `harmful:hate` | 5 | Hate speech |
| `harmful:illegal-activities` | 5 | General illegal acts |
| `harmful:illegal-drugs` | 5 | Drug manufacturing/use |
| `harmful:illegal-drugs:meth` | 5 | Meth-specific |
| `harmful:indiscriminate-weapons` | 5 | Mass-casualty weapons |
| `harmful:insults` | 5 | Personal attacks |
| `harmful:intellectual-property` | 5 | IP violations |
| `harmful:misinformation-disinformation` | 5 | False information |
| `harmful:non-violent-crime` | 5 | Fraud, theft |
| `harmful:privacy` | 5 | Privacy violations |
| `harmful:profanity` | 5 | Explicit language |
| `harmful:radicalization` | 5 | Extremist content |
| `harmful:self-harm` | 5 | Self-injury |
| `harmful:sex-crime` | 5 | Sexual assault |
| `harmful:sexual-content` | 5 | Explicit sexual content |
| `harmful:specialized-advice` | 5 | Unlicensed professional advice |
| `harmful:unsafe-practices` | 5 | Dangerous activities |
| `harmful:violent-crime` | 5 | Violence assistance |
| `harmful:weapons:ied` | 5 | Explosive devices |
| `hijacking` | 5 | Prompt hijacking |
| `pii:api-db` | 5 | PII leakage via API/DB |
| `pii:direct` | 5 | Direct PII extraction |
| `pii:session` | 5 | Cross-session PII leakage |
| `pii:social` | 5 | Social engineering for PII |
| `politics` | 5 | Political bias |
| `rbac` | 5 | Role-based access control bypass |

**Jailbreak strategies (2):**
| Strategy | Tests | Description |
|----------|-------|-------------|
| `jailbreak` | 190 | Standard jailbreak techniques |
| `jailbreak:composite` | 950 | Multi-technique composite jailbreaks |

**Red team scan results (our initial scan):**
- **1,076 passed (80.90%)** — app correctly refused or handled the attack
- **254 failed (19.10%)** — attacks that bypassed the app's defenses
- Duration: 2h 24m across 1,330 test cases

#### Phase 2: Adaptive Guardrails (Defensive)

After red teaming discovers vulnerabilities, PromptFoo generates **Adaptive Guardrails** — real-time input filters trained on the specific attack patterns that succeeded.

**API Endpoint:** `POST https://www.promptfoo.app/api/v1/guardrails/{target_id}/analyze`

**Request:**
```json
{
  "prompt": "<user input to validate>"
}
```

**Response:**
```json
{
  "allowed": true/false,
  "reason": "explanation if blocked"
}
```

**Verdict:** Binary — `"pass"` (allowed: true) or `"block"` (allowed: false)

**Key characteristic:** PromptFoo is INPUT-ONLY. It validates user prompts before they reach the LLM. It does NOT scan LLM outputs. Output scans are skipped with `verdict: "skip"`.

---

## 4. How the Tools Differ

| Capability | AIM | HiddenLayer | PromptFoo |
|-----------|-----|-------------|-----------|
| **Integration** | Inline (LiteLLM proxy) | Explicit API calls | Explicit API calls |
| **Scans Input** | Yes (pre_call) | Yes | Yes |
| **Scans Output** | Yes (post_call) | Yes (requires original prompt) | No (input only) |
| **Verdict Types** | pass / block | pass / detected / block | pass / block |
| **Policy-Aware** | Yes (AIM dashboard) | Yes (HL console policies) | Yes (learned from red team) |
| **How Policies Set** | Manual in AIM dashboard | Manual in HL console | Auto-generated from red team failures |
| **Auth Method** | API key via LiteLLM config | OAuth2 client credentials | Bearer token |
| **Sees LLM Context** | Yes (full prompt + response) | Scans content in isolation | Scans content in isolation |
| **Red Teaming** | No | No | Yes (1,330 adversarial tests) |
| **Blocking Mechanism** | HTTP 400 from LiteLLM | verdict: "block" in API response | allowed: false in API response |

---

## 5. Dynamic N-Tool Scanning Architecture

The security scanning pipeline is built on an extensible architecture that runs all enabled tools in parallel.

### Core Components (`security_service.py`)

```
SecurityTool (ABC)
├── tool_name: str       # e.g., "hidden_layer"
├── display_name: str    # e.g., "Hidden Layer"
└── scan(content, scan_type, prompt?) → {verdict, reason, scan_time_ms, details}

Implementations:
├── HiddenLayerClient(SecurityTool)
└── PromptFooClient(SecurityTool)
```

### How `security_scan()` works:

```
security_scan(content, scan_type, feature_name, prompt?)
│
├── get_active_tools()           # Discover enabled tools from config
│   ├── HL configured? → HiddenLayerClient()
│   └── PF configured? → PromptFooClient()
│
├── asyncio.gather(              # Run ALL tools in parallel
│   tool_1.scan(content, ...),
│   tool_2.scan(content, ...),
│   ...
│ )
│
└── Return {
      tool_results: {
        "hidden_layer": {verdict, reason, scan_time_ms, details},
        "promptfoo":    {verdict, reason, scan_time_ms, details}
      },
      blocked: true/false,     # true if ANY tool returned "block"
      blocked_by: ["Hidden Layer", "PromptFoo"]  # which tools blocked
    }
```

### Adding a New Security Tool

To add a new tool (e.g., Lakera, Rebuff):
1. Create a new class extending `SecurityTool`
2. Implement `tool_name`, `display_name`, and `scan()`
3. Add config fields to `config.py`
4. Add the tool to `get_active_tools()` with a config check
5. No changes needed to the scanning pipeline, logging, or frontend — they handle N tools dynamically

---

## 6. Scanning Integration Points by Feature

### Clinical Assistant (`assistant_service.py`)

```
User Question
│
├── [SCAN POINT 1] security_scan(question, "input")        ← HL + PF in parallel
│   └── If blocked → return blocked response
│
├── [SCAN POINT 2] ollama_service.generate(prompt)          ← AIM inline (pre_call + post_call)
│   ├── AIM pre_call scans prompt                             via LiteLLM proxy
│   ├── Bedrock generates response
│   ├── AIM post_call scans response
│   └── If AIM blocks → HTTP 400 → AIMBlockedException
│
├── [SCAN POINT 3] security_scan(answer, "output", prompt)  ← HL in parallel (PF skips output)
│   └── If blocked → return blocked response
│
└── Return answer to user
```

**Total: 3 scan points, up to 6 individual tool invocations**

### Document Processing (`document_service.py`)

```
Upload + Extract/Classify Request
│
├── [SCAN POINT 1] security_scan(file_content, "input")     ← HL + PF
│   └── Catches prompt injection hidden in uploaded documents
│
├── [SCAN POINT 2] ollama_service.generate(prompt)           ← AIM inline
│   └── AIMBlockedException if blocked
│
├── [SCAN POINT 3] security_scan(extracted_data, "output")   ← HL (PF skips)
│   └── Catches PII leakage in AI-extracted data
│
└── Return extracted/classified data
```

### Research Agent (`base_agent.py`)

The agent has the most intensive scanning — every iteration is scanned at multiple points:

```
Agent Task (max 15 iterations)
│
└── FOR EACH ITERATION:
    │
    ├── [SCAN POINT A] ollama_service.generate(reasoning)    ← AIM inline
    │   └── AIMBlockedException if blocked
    │
    ├── [SCAN POINT B] security_scan(reasoning, "input")     ← HL + PF
    │   └── Checks if LLM reasoning contains injection
    │
    ├── [SCAN POINT C] security_scan(tool_input, "input")    ← HL + PF
    │   └── Checks tool parameters for injection
    │
    ├── Execute tool (e.g., read_document, web_search)
    │
    └── [SCAN POINT D] security_scan(tool_output, "input")   ← HL + PF
        └── Tool outputs scanned as "INPUT" (not "output")
            because tool results are untrusted external data
            fed back to the LLM — ensures HL's prompt
            injection detector runs on the content
```

**Per iteration: 4 scan points** (1 AIM inline + 3 explicit)
**Typical 3-iteration run: 12 scan points + 3 AIM inline = 15 total security checks**

### Analytics & Reports

Same pattern as Clinical Assistant:
```
Input scan → Generate via LiteLLM (AIM inline) → Output scan
```

---

## 7. Security Logging & Observability

### Database (`security_logs` table)

Every explicit scan is logged with:
| Field | Description |
|-------|-------------|
| `feature` | Which feature triggered the scan (e.g., `clinical_assistant`, `research_agent`) |
| `scan_type` | `"input"` or `"output"` |
| `content_preview` | First 200 chars of scanned content |
| `tool_results` | JSON blob with per-tool results |
| `final_verdict` | `"pass"` or `"block"` (aggregated across all tools) |
| `agent_run_id` | Links to agent run if from an agent |
| `hl_verdict` / `hl_reason` / `hl_scan_time_ms` | Legacy columns for HiddenLayer |

### Frontend Security Dashboard

- **Filterable log table** with per-tool verdict columns
- **Security badges** on blocked messages showing which tool(s) blocked and why
- **CSV export** for compliance reporting
- **Stats view** with block rates, scan counts, tool performance

### Badge Display Logic

- **Non-blocked queries**: No badges shown (clean UI)
- **Blocked queries**: Red badge showing `"Blocked by {tool_name}: {reason}"`
- Badges render dynamically for any number of tools via shared `SecurityBadges` component

---

## 8. Security Data Flow Summary

```
                    ┌─────────────────────────────────────────────┐
                    │              USER INPUT                      │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │         EXPLICIT INPUT SCAN                  │
                    │   security_scan(input, "input")              │
                    │                                              │
                    │   ┌──────────────┐  ┌───────────────────┐   │
                    │   │ HiddenLayer  │  │    PromptFoo      │   │
                    │   │ Input scan   │  │  Guardrails scan  │   │
                    │   │ (parallel)   │  │   (parallel)      │   │
                    │   └──────┬───────┘  └────────┬──────────┘   │
                    │          └──────┬─────────────┘              │
                    │                 │                             │
                    │     blocked? ───┤──▶ YES → Return blocked    │
                    │                 │                             │
                    └─────────────────┼────────────────────────────┘
                                      │ NO
                    ┌─────────────────▼────────────────────────────┐
                    │          LLM GENERATION                       │
                    │   ollama_service.generate(prompt)             │
                    │          │                                    │
                    │          ▼                                    │
                    │   ┌──────────────┐                           │
                    │   │   LiteLLM    │                           │
                    │   │   Proxy      │                           │
                    │   │              │                           │
                    │   │  ┌────────┐  │                           │
                    │   │  │  AIM   │  │  ◄── pre_call (input)    │
                    │   │  │Guardrail│ │                           │
                    │   │  └────────┘  │                           │
                    │   │      │       │                           │
                    │   │      ▼       │                           │
                    │   │  ┌────────┐  │                           │
                    │   │  │Bedrock │  │  ◄── Claude Sonnet 4.5   │
                    │   │  └────────┘  │                           │
                    │   │      │       │                           │
                    │   │  ┌────────┐  │                           │
                    │   │  │  AIM   │  │  ◄── post_call (output)  │
                    │   │  │Guardrail│ │                           │
                    │   │  └────────┘  │                           │
                    │   └──────┬───────┘                           │
                    │          │                                    │
                    │   HTTP 400? ──▶ YES → AIMBlockedException    │
                    │          │                                    │
                    └──────────┼────────────────────────────────────┘
                               │ HTTP 200
                    ┌──────────▼────────────────────────────────────┐
                    │         EXPLICIT OUTPUT SCAN                   │
                    │   security_scan(output, "output", prompt)     │
                    │                                               │
                    │   ┌──────────────┐  ┌───────────────────┐    │
                    │   │ HiddenLayer  │  │    PromptFoo      │    │
                    │   │ Output scan  │  │    SKIPPED        │    │
                    │   │ (with prompt)│  │  (input only)     │    │
                    │   └──────┬───────┘  └───────────────────┘    │
                    │          │                                    │
                    │     blocked? ───┤──▶ YES → Return blocked    │
                    │                 │                             │
                    └─────────────────┼────────────────────────────┘
                                      │ NO
                    ┌─────────────────▼────────────────────────────┐
                    │            RESPONSE TO USER                   │
                    └──────────────────────────────────────────────┘
```

---

## 9. Environment Variables Required

| Variable | Security Tool | Purpose |
|----------|--------------|---------|
| `AIM_API_KEY` | AIM | API key for AIM guardrails (set in litellm-config.yaml) |
| `HIDDENLAYER_CLIENT_ID` | HiddenLayer | OAuth2 client ID |
| `HIDDENLAYER_CLIENT_SECRET` | HiddenLayer | OAuth2 client secret |
| `HIDDENLAYER_API_URL` | HiddenLayer | API base URL (`https://api.hiddenlayer.ai`) |
| `HIDDENLAYER_PROJECT_ID` | HiddenLayer | Project ID for policy scoping |
| `PROMPTFOO_API_KEY` | PromptFoo | Bearer token for Guardrails API |
| `PROMPTFOO_TARGET_ID` | PromptFoo | Target ID for Adaptive Guardrails |
| `PROMPTFOO_API_URL` | PromptFoo | Base URL (`https://www.promptfoo.app`) |
| `LITELLM_MASTER_KEY` | LiteLLM/AIM | Master key for LiteLLM proxy |
| `LITELLM_VIRTUAL_KEY` | LiteLLM/AIM | Virtual key linking to AIM Guard |
