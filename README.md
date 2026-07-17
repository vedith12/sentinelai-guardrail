# 🛡️ SentinelAI — AI Output Policy Guardrail Service

> **A production-grade, policy-driven middleware layer that inspects, evaluates, and sanitizes AI-generated outputs in real time before they reach your users.**

---

## Overview

SentinelAI sits between your AI model and your end-users, acting as an intelligent gatekeeper. Every output produced by an LLM is evaluated against a configurable policy library. Depending on the findings, SentinelAI can **approve**, **warn**, **rewrite**, **flag for human review**, or outright **block** the response — all within a single API call.

It combines **fast deterministic checks** (regex-based PII scanning, keyword filtering) with **LLM-powered semantic judgment** to catch nuanced policy violations that simple rules can't detect.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔍 **Deterministic Checks** | Lightning-fast regex scanning for PII (emails, phone numbers, credit cards, API keys), forbidden keywords, and JSON schema validation |
| 🤖 **LLM Judge** | Uses a language model as an expert policy evaluator for semantic/contextual violations (toxicity, hallucinations, brand voice, etc.) |
| ⚖️ **Consensus Judging** | Runs two independent LLM judges for high-severity policies; disagreements are automatically escalated to human review |
| ✏️ **Smart Rewriting** | Auto-redacts PII with typed placeholders (`[EMAIL_REDACTED]`) and uses LLM rewriting to fix tone or brand policy violations |
| 📋 **Policy-as-Config** | Policies are database-driven and bootstrapped from a `policies.yaml` file — add or edit policies without changing code |
| 📊 **Audit Trail** | Every evaluation is persisted as an `EvaluationLog`. Blocked/review decisions automatically create an `AuditReview` record for human oversight |
| 🔌 **Multi-LLM Support** | Pluggable LLM backend — works with **OpenRouter** (any model) or **Google Gemini** out of the box |
| 🌿 **Optional Presidio** | Toggle Microsoft Presidio for enterprise-grade PII detection via the `USE_PRESIDIO` flag |

---

## 🏗️ Architecture

```
Your App / LLM Output
        │
        ▼
┌───────────────────────────────────┐
│         Evaluation Pipeline        │
│                                   │
│  1. Fetch Active Policies from DB  │
│                                   │
│  2. ⚡ Deterministic Checks (fast) │
│     • PII Scan (regex / Presidio)  │
│     • Keyword / Regex Filter       │
│     • JSON Schema Validation       │
│                                   │
│  3. 🤖 LLM Judge (if not blocked) │
│     • Per-policy semantic eval     │
│     • Consensus mode (high-sev.)   │
│                                   │
│  4. 🎯 Decision Resolution         │
│     block > review > rewrite >     │
│     warn > approve                 │
│                                   │
│  5. ✏️  Smart Rewriter (if needed) │
│     • Deterministic PII redaction  │
│     • LLM-based tone/policy fix    │
│                                   │
│  6. 📦 Log → DB (Audit Trail)      │
└───────────────────────────────────┘
        │
        ▼
   Final Output + Decision + Findings
```

---

## 📁 Project Structure

```
sentinelAI/
├── app/
│   ├── config.py              # Settings (LLM provider, DB URL, Presidio flag)
│   ├── db.py                  # DB engine, session, policy seeding from YAML
│   ├── models.py              # Pydantic API schemas + SQLModel DB tables
│   ├── policies/
│   │   └── policies.yaml      # Default policy definitions (seeded into DB)
│   └── services/
│       ├── deterministic.py   # PII regex scanner & keyword checker
│       ├── evaluator.py       # Main orchestrator pipeline
│       ├── llm_judge.py       # LLM provider calls + policy evaluation logic
│       └── rewriter.py        # Deterministic PII redaction + LLM rewriting
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL (or update `DATABASE_URL` to use SQLite for local dev)
- An [OpenRouter](https://openrouter.ai) API key **or** a [Google Gemini](https://ai.google.dev/) API key

### 1. Clone & Install

```bash
git clone https://github.com/your-username/sentinelai.git
cd sentinelai

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/guardrail

# LLM Provider — pick one
LLM_PROVIDER=openrouter          # or: gemini
OPENROUTER_API_KEY=sk-or-...
GEMINI_API_KEY=AIza...

# Model (OpenRouter format or Gemini model name)
LLM_MODEL=google/gemma-2-9b-it:free

# Optional: Use Microsoft Presidio for enterprise PII detection
USE_PRESIDIO=false
```

### 3. Seed the Database & Run

```bash
# The service auto-creates tables and seeds policies.yaml on first start
uvicorn app.main:app --reload
```

---

## 🔧 Policy Configuration

Policies live in `app/policies/policies.yaml` and are seeded into the database on startup (if the table is empty). Each policy defines:

| Field | Description |
|---|---|
| `name` | Unique identifier (e.g., `pii_leakage`, `toxic_content`) |
| `category` | Grouping label (e.g., `safety`, `compliance`, `brand`) |
| `description` | Human-readable description for the LLM judge |
| `severity` | `low`, `medium`, or `high` |
| `action` | `approve`, `warn`, `rewrite`, `review`, or `block` |
| `detection_strategy` | `deterministic` or `llm_judge` |
| `rules` | Array of `{name, pattern, type}` objects for deterministic checks |
| `examples` | Few-shot examples of violations for the LLM judge |

---

## 📡 API Usage

### `POST /evaluate`

Evaluate an AI output against all active policies.

**Request:**
```json
{
  "prompt": "Tell me about medication dosages",
  "output": "You should take 1000mg of ibuprofen every 4 hours.",
  "features": ["medical_advice", "toxic_content"]
}
```
> `features` is optional. Omit it to run all active policies.

**Response:**
```json
{
  "original_output": "You should take 1000mg of ibuprofen every 4 hours.",
  "final_output": "Please consult a healthcare professional for specific dosage guidance.",
  "decision": "rewrite",
  "findings": [
    {
      "policy_name": "medical_advice",
      "decision": "rewrite",
      "severity": "high",
      "evidence": "1000mg of ibuprofen every 4 hours",
      "reason": "Output provides specific medication dosage which constitutes medical advice."
    }
  ],
  "latency_ms": 847.3
}
```

### Decision Hierarchy

| Decision | Meaning |
|---|---|
| `approve` | Clean — no violations found |
| `warn` | Soft violation — output passes but findings are flagged |
| `rewrite` | Output modified to remove/soften violations |
| `review` | Flagged for human review (LLM uncertainty or consensus disagreement) |
| `block` | Output fully suppressed — hard policy violation |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI |
| **ORM / DB** | SQLModel + PostgreSQL |
| **Schema Validation** | Pydantic v2 |
| **LLM Calls** | `httpx` (async-ready) |
| **LLM Providers** | OpenRouter, Google Gemini |
| **PII Detection** | Regex (built-in) + Microsoft Presidio (optional) |
| **Policy Seeding** | YAML → PostgreSQL |

---

## 🗺️ Roadmap

- [ ] FastAPI router & main entry point (`app/main.py`)
- [ ] `GET /policies` — CRUD API for managing policies at runtime
- [ ] `GET /logs` — Paginated evaluation log viewer
- [ ] `PATCH /audit/{id}` — Human review override endpoint
- [ ] Async LLM calls with `httpx.AsyncClient`
- [ ] Docker + Docker Compose setup
- [ ] Prometheus metrics endpoint
- [ ] Webhook support for real-time review notifications

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
