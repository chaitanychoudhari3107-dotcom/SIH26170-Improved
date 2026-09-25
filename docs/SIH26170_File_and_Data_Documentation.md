# SIH26170 — Semiconductor Reliability Analysis Application
# File Structure & Data/Dataset Documentation

**Project:** Smart India Hackathon 2026 — Problem Statement 26170 (ISRO)  
**Project Root Directory:** `C:\Users\admin\Desktop\sih26170`  
**Dataset Benchmark:** `SIH26170-FINAL-01` (Frozen Release, Split Protocol `LOTSPLIT-05`)  
**Document Purpose:** Internal Engineering Specification, File-by-File Guide, and Dataset Dictionary  
**Intended Audience:** Backend/Frontend Developers, Data Engineers, and System Architects  

---

## 1. Complete Project Directory Tree

Below is the verified ASCII directory tree of the SIH26170 project repository (excluding `.git`, `node_modules`, `__pycache__`, and `dist` build caches):

```
sih26170/
|-- backend/
|   |-- _test_loader.py (639 B)
|   |-- data_loader.py (21,894 B)
|   |-- database.py (467 B) [Legacy]
|   |-- explainability/
|   |   \-- explainability_report.py (8,013 B) [Legacy]
|   |-- fusions/
|   |   \-- fusion.py (6,291 B) [Legacy standalone prototype]
|   |-- main.py (6,729 B)
|   |-- models.py (401 B) [Legacy]
|   |-- modules/
|   |-- operational/
|   |   |-- Operational_API_Contract.json (2,392 B)
|   |   |-- Operational_DB_Schema.sql (2,731 B)
|   |   |-- operational_db.py (2,007 B)
|   |   \-- operational_routes.py (16,503 B)
|   |-- operational.db (40,960 B) [Active SQLite operational store]
|   |-- schemas.py (177 B) [Legacy]
|   |-- sih26170.db (20,480 B) [Legacy SQLite store]
|   \-- test_integration.py (5,790 B) [12 automated integration tests]
|-- data/
|   |-- _archive/ [Deprecated 297-row demo data & intermediate outputs]
|   |   |-- ModuleB_Final_Holdout_Predictions.csv (799,995 B)
|   |   |-- explainability_report.csv (132,593 B)
|   |   |-- fused_component_summary.csv (84,758 B)
|   |   |-- modulea_component_summary.csv (42,441 B)
|   |   |-- moduleb_component_summary.csv (85,853 B)
|   |   \-- moduleb_predictions_long.csv (475,585 B)
|   |-- final/ [Authoritative 1,343-part benchmark holdout]
|   |   |-- Fusion_Dryrun.json (2,253 B)
|   |   |-- Fusion_Joined_Holdout.csv (839,856 B) [AUTHORITATIVE GROUND TRUTH]
|   |   |-- ModuleA_Final_Holdout_0h.csv (158,172 B)
|   |   |-- ModuleA_Final_Holdout_24h.csv (159,722 B)
|   |   |-- ModuleA_Final_Holdout_96h.csv (160,403 B)
|   |   |-- ModuleA_Final_Holdout_168h.csv (165,118 B)
|   |   |-- ModuleA_Release_Manifest.json (2,870 B)
|   |   |-- ModuleB_Final_Holdout_Predictions.csv (799,995 B)
|   |   |-- ModuleB_Holdout.csv (191,974 B)
|   |   \-- ModuleB_Release_Manifest.json (10,794 B)
|   |-- operational/ [Operational templates and guides]
|   |   |-- Operational_Input_Example_12Rows.csv (1,117 B)
|   |   |-- Operational_Measurement_Input_Template.csv (157 B)
|   |   \-- README_Operational_Layer.md (1,721 B)
|   \-- reference/ [Specification limits, contracts & manifests]
|       |-- Dataset_Version_Safe.json (678 B)
|       |-- Device_Specs.csv (4,869 B)
|       |-- FINAL_APPROVAL.md (1,872 B)
|       |-- Fusion_Output_Contract.csv (186 B)
|       |-- Integration_Contract_Safe.json (1,346 B)
|       |-- Integration_Sample_60_TrainOnly.csv (15,617 B)
|       |-- ModuleA_Output_Contract.csv (99 B)
|       |-- ModuleB_Output_Contract.csv (463 B)
|       |-- Safe_Lot_Split_Manifest.csv (1,809 B)
|       \-- Schema_Data_Dictionary.csv (2,175 B)
|-- docs/
|   |-- SESSION_STATE_2026-09-22.md (2,658 B)
|   |-- SIH26170_File_and_Data_Documentation.md [This document]
|   |-- SIH26170_Prototype_Documentation.md (64,260 B) [System report & demo guide]
|   |-- implementation_plan.md (27,814 B)
|   \-- walkthrough.md (8,042 B)
|-- frontend/
|   |-- .gitignore (253 B)
|   |-- .oxlintrc.json (231 B)
|   |-- README.md (1,009 B)
|   |-- index.html (381 B)
|   |-- package.json (552 B)
|   |-- package-lock.json (58,837 B)
|   |-- public/
|   |   |-- favicon.svg (9,522 B)
|   |   \-- icons.svg (5,031 B)
|   |-- src/
|   |   |-- App.css (167 B)
|   |   |-- App.jsx (1,149 B)
|   |   |-- assets/ (hero.png, react.svg, vite.svg)
|   |   |-- components/
|   |   |   |-- layout/ (PageHeader.jsx, PageHeader.css, Sidebar.jsx, Sidebar.css)
|   |   |   \-- ui/ (Badge.jsx, Card.jsx, DataTable.jsx, EmptyState.jsx, ErrorState.jsx, LoadingState.jsx, SearchInput.jsx, ui.css)
|   |   |-- hooks/ (useApi.js)
|   |   |-- index.css (121 B)
|   |   |-- main.jsx (242 B)
|   |   |-- pages/
|   |   |   |-- Analyze.jsx (6,936 B) & Analyze.css (3,676 B)
|   |   |   |-- ComponentDetail.jsx (18,433 B) & ComponentDetail.css (13,674 B)
|   |   |   |-- Components.jsx (9,424 B) & Components.css (5,259 B)
|   |   |   |-- Data.jsx (16,830 B) & Data.css (8,006 B)
|   |   |   |-- Models.jsx (18,890 B) & Models.css (8,461 B)
|   |   |   |-- Overview.jsx (16,493 B) & Overview.css (10,046 B)
|   |   |   \-- System.jsx (21,484 B) & System.css (10,582 B)
|   |   |-- services/ (api.js)
|   |   \-- styles/ (global.css, tokens.css)
|   \-- vite.config.js (217 B)
|-- incoming/ [Frozen upstream release packets & verification artifacts]
|   |-- SIH26170_FINAL_Team_Group_Bundle.zip (985 KB)
|   |-- SIH26170_ModuleA_FINAL01.zip (3.51 MB)
|   |-- SIH26170_ModuleB_FINAL01_RC2.zip (1.30 MB)
|   |-- chaitanya/ (Integration & distribution packets)
|   |-- nirmik/ (SIH26170_ModuleB_FINAL01_RC2 source, notebooks & tests)
|   \-- riddhi/ (SIH26170_ModuleA_FINAL01 source, packets & tests)
\-- tests/ (Directory reserved for end-to-end testing)
```

---

## 2. File-by-File Documentation

### Core Backend Source Files (`backend/`)

#### 1. `backend/data_loader.py`
- **Purpose:** In-memory analytical data engine. Loads all authoritative CSV benchmark data, manifests, and references at module import time; computes fused verdicts; constructs natural language explainability; and provides sub-5ms indexed lookups.
- **Inputs:**
  - `data/final/Fusion_Joined_Holdout.csv`
  - `data/final/ModuleA_Final_Holdout_{0,24,96,168}h.csv`
  - `data/final/ModuleB_Final_Holdout_Predictions.csv`
  - `data/final/ModuleB_Holdout.csv`
  - `data/final/ModuleA_Release_Manifest.json` & `ModuleB_Release_Manifest.json`
  - `data/reference/Device_Specs.csv` & `Schema_Data_Dictionary.csv`
  - `incoming/riddhi/SIH26170_ModuleA_FINAL01/results/` evaluation CSVs.
- **Outputs:** In-memory pandas DataFrames (`fusion_df`, `module_a_dfs`, `module_b_df`, etc.) and cleaned JSON serializable dictionaries.
- **Important Functions:**
  - `compute_verdict(row)`: Implements the fusion logic ($23 \text{ CONFIRMED} + 5 \text{ wearout breaches} \to 28 \text{ REJECT}$; $202 \text{ MONITOR}$; $1,113 \text{ PASS}$).
  - `generate_explanation(row)`: Synthesizes plain-English physical failure explanations from reason codes and evidence columns.
  - `get_component(cid)`: Returns comprehensive diagnostic payload for a component.
  - `get_component_module_a_epochs(cid)`: Returns 4-epoch progression dictionary.
  - `get_lots_summary()`: Computes component counts and mean risk scores across all 18 holdout production lots.
  - `get_evaluation_metrics()`: Returns confusion matrices, sensitivity analyses, epoch evolution, and per-variant statistics.
  - `get_pipeline_architecture()`: Returns 7-stage data lineage metadata.
  - `_clean(obj)`: Recursively replaces `NaN`, `Infinity`, and NumPy types with `None` to prevent JSON serialization errors.
- **Dependencies:** `pandas`, `numpy`, `json`, `pathlib`, `math`.
- **Used By:** `backend/main.py`, `backend/test_integration.py`.

#### 2. `backend/main.py`
- **Purpose:** Primary FastAPI application server. Declares CORS middleware, mounts analytical endpoints, mounts operational routers, and serves API consumers on port `8001`.
- **Inputs:** HTTP requests from client browser or curl.
- **Outputs:** JSON responses conforming to REST contracts.
- **Important Routes:**
  - `GET /`: Health check.
  - `GET /api/analysis/search`: Prefix search by component ID or lot ID.
  - `GET /api/analysis/summary`: Fleet aggregate totals.
  - `GET /api/analysis/{component_id}`: Full analytical detail.
  - `GET /api/analysis/{component_id}/module-a`: Multi-epoch progression.
  - `GET /api/components`: Paginated fleet query with filters.
  - `GET /api/lots`: Summary of 18 production lots.
  - `GET /api/models/evaluation`: Authoritative confusion matrices and D2 sensitivity.
  - `GET /api/models/info`: Release manifests and integration metadata.
  - `GET /api/pipeline/architecture`: 7-stage lineage pipeline.
  - `GET /api/system/status`: Real-time service telemetry.
- **Dependencies:** `fastapi`, `fastapi.middleware.cors`, `data_loader`, `operational.operational_routes`.
- **Used By:** React frontend, test scripts, external API consumers.

#### 3. `backend/operational/operational_routes.py`
- **Purpose:** FastAPI APIRouter handling operational test floor data ingestion, component registration, and trajectory retrieval.
- **Inputs:** JSON payloads from the Operational Data Studio wizard.
- **Outputs:** Database write confirmations and operational summary metrics.
- **Important Routes:**
  - `POST /api/measurements`: Validates and inserts a single epoch measurement into SQLite `operational.db`.
  - `GET /api/dashboard/summary`: Returns counts of registered operational components, total measurements, and recent audit logs.
  - `GET /api/components/{component_id}`: Fetches operational component metadata.
  - `GET /api/components/{component_id}/trajectory`: Retrieves chronological measurements for a component.
- **Dependencies:** `fastapi`, `operational.operational_db`.
- **Used By:** `backend/main.py`, `frontend/src/pages/Data.jsx`.

#### 4. `backend/operational/operational_db.py`
- **Purpose:** SQLite database driver for `backend/operational.db`. Enforces WAL mode, foreign keys, schema initialization, and transactional integrity.
- **Inputs:** Parametric measurement values.
- **Outputs:** SQLite records and rows.
- **Important Functions:**
  - `init_db()`: Executes `Operational_DB_Schema.sql`.
  - `add_component()`: Registers new die/package.
  - `add_measurement()`: Ingests epoch readings with float positivity checks.
  - `get_dashboard_summary()`: Gathers operational telemetry.
- **Dependencies:** `sqlite3`, `pathlib`, `datetime`.
- **Used By:** `backend/operational/operational_routes.py`.

#### 5. `backend/test_integration.py`
- **Purpose:** Automated integration test suite. Executes 12 comprehensive tests across all backend routes to prevent regressions.
- **Inputs:** Local FastAPI test client (`TestClient(app)`).
- **Outputs:** Unit test pass/fail results.
- **Tests Implemented:** Health check, system status, summary, search, component detail, pagination, model manifests, operational lifecycle, reference specs, evaluation metrics, lots summary, pipeline architecture.
- **Dependencies:** `unittest`, `fastapi.testclient`, `backend/main.py`.
- **Used By:** Continuous integration, development verification.

---

### Core Frontend Source Files (`frontend/src/`)

#### 1. `frontend/src/services/api.js`
- **Purpose:** Centralized HTTP client wrapper.
- **Implementation:** Wraps native `fetch` with error interception and sets base URL to `http://127.0.0.1:8001`.
- **Used By:** All React pages and custom hooks.

#### 2. `frontend/src/hooks/useApi.js`
- **Purpose:** Custom React hook for asynchronous data fetching.
- **Returns:** `{ data, loading, error, refetch }`.
- **Used By:** `Overview.jsx`, `ComponentDetail.jsx`, `Components.jsx`, `Models.jsx`, `System.jsx`, `Data.jsx`.

#### 3. `frontend/src/pages/Overview.jsx` & `Overview.css`
- **Purpose:** Executive fleet dashboard.
- **Renders:** KPI stat cards, 4-epoch progression banner, Module A/B/Fusion cards, live evaluation snapshot, variant bars, recent holdout table.

#### 4. `frontend/src/pages/Analyze.jsx` & `Analyze.css`
- **Purpose:** Interactive search and triage terminal.
- **Renders:** Search input with auto-focus, quick-select chips (`C00158`, `C00445`, `C00843`, etc.), search results card with direct jump.

#### 5. `frontend/src/pages/ComponentDetail.jsx` & `ComponentDetail.css`
- **Purpose:** Comprehensive single-component forensic studio.
- **Renders:** Fused verdict banner, Module A diagnostic card with gauge, plain-English explainability, 6 Module B parameter cards with **Recharts P95 vs Limit visualizers**, multi-epoch progression table, baseline historical trajectory.

#### 6. `frontend/src/pages/Components.jsx` & `Components.css`
- **Purpose:** High-density fleet browser.
- **Renders:** Multi-parameter filter toolbar (Search, Verdict, Variant, 18-Lot dropdown), sortable data table, pagination controls.

#### 7. `frontend/src/pages/Models.jsx` & `Models.css`
- **Purpose:** Model verification and mathematical evaluation console.
- **Renders:** Interactive 2x2 confusion matrix (Baseline vs Relaxed toggle), metric derivations, Decision D2 sensitivity table ($25 \to 24$ FN tradeoff), burn-in epoch evolution table, per-variant breakdown, manifest checklists.

#### 8. `frontend/src/pages/Data.jsx` & `Data.css`
- **Purpose:** Operational test floor data acquisition studio.
- **Renders:** Benchmark isolation banner, operational summary metrics, audit tables, 4-step measurement wizard with numeric validation.

#### 9. `frontend/src/pages/System.jsx` & `System.css`
- **Purpose:** Architecture command center and data lineage explorer.
- **Renders:** System telemetry cards, interactive 7-stage pipeline diagram with contextual stage drawer, Device Physical Specs table (18 limits), Schema Data Dictionary (28 definitions).

#### 10. `frontend/src/styles/tokens.css`
- **Purpose:** LATENT obsidian design tokens.
- **Defines:** Deep obsidian surface colors (`--bg-primary: #030712`, `--bg-surface: #0b1120`), borders (`--border-subtle: rgba(255,255,255,0.08)`), status glows (`--status-pass: #10b981`, `--status-reject: #ef4444`, `--status-monitor: #f59e0b`), monospace typography (`JetBrains Mono`).

---

## 3. Backend Structure & Connections

```
                                  main.py (:8001)
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
          data_loader.py                             operational_routes.py
                 │                                               │
        ┌────────┴────────┐                             ┌────────┴────────┐
        ▼                 ▼                             ▼                 ▼
  data/final/       incoming/.../results/         operational_db.py  operational.db
  (Immutable CSVs)   (Evaluation Data)            (SQLite Driver)    (SQLite Tables)
```

1. **`main.py`** boots the application, configures CORS for `http://localhost:5174`, and includes `operational_routes`.
2. **`data_loader.py`** reads from `data/final/` and `incoming/` at startup. It structures dataframes in memory and caches indices by `component_id`. It handles all read queries for the analytical frontend.
3. **`operational_routes.py`** and **`operational_db.py`** manage test floor data. When an operator commits a measurement via the UI, it writes exclusively to `operational.db`.
4. **Physical Separation:** `data_loader.py` never writes to `data/final/` or `operational.db`. `operational_db.py` never writes to `data/final/`. This architectural firewall guarantees zero benchmark contamination.

---

## 4. Frontend Structure & API Route Mapping

| Frontend Page Component | Route Path | Backing API Endpoints | Trigger / Interaction |
| :--- | :--- | :--- | :--- |
| **`Overview.jsx`** | `/` | `GET /api/analysis/summary`<br/>`GET /api/models/evaluation`<br/>`GET /api/components?page=1&per_page=8` | Page load; refresh button |
| **`Analyze.jsx`** | `/analyze` | `GET /api/analysis/search?q={query}` | Text input typing; chip clicks |
| **`ComponentDetail.jsx`** | `/analyze/:id` | `GET /api/analysis/{id}`<br/>`GET /api/analysis/{id}/module-a` | Route param change; epoch tab click |
| **`Components.jsx`** | `/components` | `GET /api/components`<br/>`GET /api/lots` | Filter dropdowns; pagination buttons |
| **`Models.jsx`** | `/models` | `GET /api/models/evaluation`<br/>`GET /api/models/info` | Page load; operating point toggle |
| **`Data.jsx`** | `/data` | `GET /api/dashboard/summary`<br/>`POST /api/measurements` | Tab switch; wizard form submission |
| **`System.jsx`** | `/system` | `GET /api/system/status`<br/>`GET /api/pipeline/architecture`<br/>`GET /api/reference/specs`<br/>`GET /api/reference/dictionary` | Page load; stage node clicks; spec filter chips |

---

## 5. Data Directory Audit: Complete Inventory

Below is an exhaustive audit of every data file in `data/`:

| Relative Path | Format | Rows | Cols | Provenance / Role | Authoritative? | Consumed By | Produced By |
| :--- | :---: | :---: | :---: | :--- | :---: | :--- | :--- |
| **`final/Fusion_Joined_Holdout.csv`** | CSV | **1,343** | **45** | **Authoritative Holdout Ground Truth**; pre-joined Module A & B outputs | **YES** | `backend/data_loader.py` | Fusion pipeline script |
| **`final/ModuleA_Final_Holdout_0h.csv`** | CSV | 1,343 | 13 | Module A screening scored at 0h | **YES** | `data_loader.py` | Module A Release Candidate |
| **`final/ModuleA_Final_Holdout_24h.csv`**| CSV | 1,343 | 13 | Module A screening scored at 24h | **YES** | `data_loader.py` | Module A Release Candidate |
| **`final/ModuleA_Final_Holdout_96h.csv`**| CSV | 1,343 | 13 | Module A screening scored at 96h | **YES** | `data_loader.py` | Module A Release Candidate |
| **`final/ModuleA_Final_Holdout_168h.csv`**| CSV| 1,343 | 13 | Module A screening scored at 168h | **YES** | `data_loader.py` | Module A Release Candidate |
| **`final/ModuleB_Final_Holdout_Predictions.csv`** | CSV | 1,343 | 39 | Module B 168h drift predictions + P95 bounds + evidence | **YES** | `data_loader.py` | Module B Release Candidate |
| **`final/ModuleB_Holdout.csv`** | CSV | 1,343 | 16 | Historical 0h & 24h baseline readings with lot IDs | **YES** | `data_loader.py` | Generator `LOTSPLIT-05` |
| **`final/Fusion_Dryrun.json`** | JSON | N/A | N/A | 9-point integration contract verification audit | **YES** | Backend reference | Anushka integration test |
| **`final/ModuleA_Release_Manifest.json`** | JSON | N/A | N/A | Module A freeze metadata & SHA-256 digests | **YES** | `data_loader.py` | Stage 11 release script |
| **`final/ModuleB_Release_Manifest.json`** | JSON | N/A | N/A | Module B freeze metadata, contracts & rules | **YES** | `data_loader.py` | Release script |
| **`operational/Operational_Input_Example_12Rows.csv`** | CSV | 12 | 11 | Reference multi-epoch test data for 3 components | Derived | Demonstration/Testing | Test generator |
| **`operational/Operational_Measurement_Input_Template.csv`**| CSV | 0 | 11 | Empty CSV template for bulk test floor uploads | Template | Operators | Specification |
| **`operational/README_Operational_Layer.md`** | MD | N/A | N/A | Operational architecture guidelines by Anushka | Reference | Documentation | Engineering team |
| **`reference/Device_Specs.csv`** | CSV | 18 | 11 | Static physical limits across CMOS_A/B/C | **YES** | `data_loader.py`, `/system` | Tanisha (Domain Lead) |
| **`reference/Schema_Data_Dictionary.csv`** | CSV | 28 | 5 | Data dictionary defining all 28 schema attributes | **YES** | `data_loader.py`, `/system` | Engineering team |
| **`reference/Dataset_Version_Safe.json`** | JSON | N/A | N/A | Dataset ID `SIH26170-FINAL-01` metadata | **YES** | `data_loader.py` | Chaitanya (Data Architect) |
| **`reference/Safe_Lot_Split_Manifest.csv`** | CSV | 72 | 4 | Complete manifest of all 72 lots across splits | **YES** | Verification scripts | Chaitanya (Data Architect) |
| **`reference/Integration_Sample_60_TrainOnly.csv`** | CSV | 60 | 28 | Training sample for integration dryruns | Derived | Integration tests | Pre-freeze test |
| **`_archive/explainability_report.csv`** | CSV | 297 | 27 | Deprecated 297-row demo data | Obsolete | Isolated archive | Prototype session |
| **`_archive/fused_component_summary.csv`** | CSV | 297 | 20 | Deprecated 297-row demo fusion | Obsolete | Isolated archive | Prototype session |
| **`_archive/modulea_component_summary.csv`** | CSV | 297 | 10 | Deprecated 297-row Module A summary | Obsolete | Isolated archive | Prototype session |
| **`_archive/moduleb_component_summary.csv`** | CSV | 297 | 22 | Deprecated 297-row Module B summary | Obsolete | Isolated archive | Prototype session |
| **`_archive/moduleb_predictions_long.csv`** | CSV | 1,782 | 32 | Deprecated long-format predictions (297x6) | Obsolete | Isolated archive | Prototype session |

---

## 6. Dataset Column Dictionaries

### A. Authoritative Ground Truth: `Fusion_Joined_Holdout.csv` (45 Columns)

| Column Index | Column Name | Data Type | Physical Meaning & Range | Module Source |
| :---: | :--- | :---: | :--- | :---: |
| 1 | `component_id` | String | Unique component identifier (`C00158`–`C05320`) | Both |
| 2 | `module_a_score` | Float | Multi-epoch screening anomaly score $[0.000, 1.000]$ | Module A |
| 3 | `module_a_disposition` | String | Screening verdict: `PASS` or `MONITOR` | Module A |
| 4 | `module_a_primary_parameter`| String | Channel with highest observed deviation | Module A |
| 5 | `module_a_reason_codes` | String | Pipe-delimited tokens (`A_STATIC_LIMIT_EXCEEDED`, etc.) | Module A |
| 6 | `module_a_evidence_tier` | String | Evidence classification: `PASS`, `MONITOR`, `CONFIRMED` | Module A |
| 7–12 | `predicted_{PARAM}_168h` | Float | Huber point forecast for 168h end-of-test value | Module B |
| 13–18| `module_b_p95_{PARAM}_168h` | Float | Conformalized upper 95th percentile confidence bound | Module B |
| 19 | `module_b_primary_parameter`| String | Parameter exhibiting maximum projected drift | Module B |
| 20 | `module_b_reason_codes` | String | Pipe-delimited warning tokens (`B_HIGH_FORECAST_DRIFT`, etc.)| Module B |
| 21,25,29,33,37,41 | `evidence_{PARAM}_limit` | Float | Static datasheet specification maximum limit | Device Specs |
| 22,26,30,34,38,42 | `evidence_{PARAM}_pred_frac_of_limit` | Float | Predicted 168h value as fraction of limit ($\hat{x}_{168} / \text{limit}$) | Module B |
| 23,27,31,35,39,43 | `evidence_{PARAM}_pred_rel_delta_from_24h` | Float | Predicted relative drift from 24h baseline ($(\hat{x}_{168} - x_{24})/x_{24}$) | Module B |
| 24,28,32,36,40,44 | `evidence_{PARAM}_lot_rel_dev_24h` | Float | 24h lot-relative deviation $z$-score | Module B |
| 45 | `b_evidence_status` | String | Quality status of evidence (`OK`, `LIMIT_UNKNOWN`, etc.) | Module B |

*Note: `{PARAM}` spans the 6 monitored physical channels:*
`IDDQ`, `Input_Leakage_Current`, `Active_Supply_Current`, `Propagation_Delay`, `Output_Rise_Time`, `Output_Fall_Time`.

### B. Module A Output Contract: `ModuleA_Final_Holdout_168h.csv` (13 Columns)

| Index | Column Name | Type | Description |
| :---: | :--- | :---: | :--- |
| 1 | `component_id` | String | Unique component ID |
| 2 | `module_a_score` | Float | Composite score in $[0, 1]$; $\ge 0.90$ indicates spec breach |
| 3 | `module_a_disposition` | String | Operating disposition: `PASS` or `MONITOR` |
| 4 | `module_a_primary_parameter` | String | Dominant physical channel driving the anomaly |
| 5 | `module_a_reason_codes` | String | Pipe-delimited explanatory codes |
| 6 | `module_a_evidence_tier` | String | Discrete tier: `PASS`, `MONITOR`, `CONFIRMED` |
| 7 | `module_a_attribution_margin` | Float | Numerical gap between top failing parameter and runner-up |
| 8 | `statistical_score` | Float | Scaled robust-z score against lot cohort ($0.0–0.9$) |
| 9 | `spec_exceedance_ratio` | Float | Fractional limit exceedance ($> 0.0$ if out of spec) |
| 10 | `scored_epoch_h` | Integer | Epoch milestone evaluated (`168`) |
| 11 | `analysis_status` | String | Evaluation status (`OK`) |
| 12 | `model_version` | String | Version identifier (`ModuleA-FINAL01`) |
| 13 | `dataset_id` | String | Benchmark identifier (`SIH26170-FINAL-01`) |

---

## 7. Data Lineage

The authoritative pipeline flows through discrete stages:

```
[incoming/ (Raw Benchmark Archives)]
      │
      ▼  (Chaitanya: 01_split_structure.py / LOTSPLIT-05)
[data/final/ModuleB_Holdout.csv + Epoch Files]
      │
      ├──────────────────────────────────────────────┐
      ▼ (Riddhi: 08_predict_holdout.py)              ▼ (Nirmik: 12_predict_holdout.py)
[ModuleA_Final_Holdout_{0,24,96,168}h.csv]      [ModuleB_Final_Holdout_Predictions.csv]
      │                                              │
      └──────────────────────┬───────────────────────┘
                             │
                             ▼ (Anushka: 15_fusion_joined_holdout.py)
              [data/final/Fusion_Joined_Holdout.csv]
                             │
                             ▼ (FastAPI data_loader.py startup)
                     [In-Memory DataFrames]
                             │
                             ▼ (REST Endpoints on :8001)
                     [React Console on :5174]
```

1. **Raw Generation:** `incoming/chaitanya` partitions 5,400 parts into 42 training lots, 12 calibration lots, and 18 holdout lots (`LOTSPLIT-05`).
2. **Holdout Extraction:** 1,343 holdout components are isolated with zero leakage into `ModuleB_Holdout.csv`.
3. **Module A Scoring:** Riddhi's frozen pipeline (`module_a_final01.joblib`) scores all 4 epochs, writing `ModuleA_Final_Holdout_{0,24,96,168}h.csv`.
4. **Module B Prediction:** Nirmik's frozen Huber regressors consume 0h and 24h readings, writing `ModuleB_Final_Holdout_Predictions.csv`.
5. **Fusion Joining:** Anushka joins Module A 168h and Module B on `component_id`, writing `Fusion_Joined_Holdout.csv`.
6. **Backend Ingestion:** FastAPI's `data_loader.py` ingests the joined dataset into memory, adds the `fused_verdict` column, and serves REST routes.

---

## 8. Authoritative Final Dataset Summary

- **File Path:** `C:\Users\admin\Desktop\sih26170\data\final\Fusion_Joined_Holdout.csv`
- **Total Rows:** `1,343`
- **Total Columns:** `45`
- **Unique Components:** `1,343` (C00158 through C05320; contiguous within each lot)
- **Production Lots:** Exactly 18 whole lots (6 CMOS_A, 6 CMOS_B, 6 CMOS_C):
  - `A_L03`, `A_L05`, `A_L07`, `A_L09`, `A_L10`, `A_L15` (441 components)
  - `B_L02`, `B_L04`, `B_L08`, `B_L14`, `B_L20`, `B_L22` (458 components)
  - `C_L01`, `C_L06`, `C_L12`, `C_L16`, `C_L18`, `C_L24` (444 components)
- **Verdict Distribution:**
  - `PASS`: **1,113** components ($82.87\%$)
  - `MONITOR`: **202** components ($15.04\%$)
  - `REJECT`: **28** components ($2.09\%$)

---

## 9. Operational Data Documentation (`operational.db`)

### SQLite Schema (`backend/operational/Operational_DB_Schema.sql`)
The operational database contains 3 core tables:

1. **`components` Table:**
   ```sql
   CREATE TABLE components (
       component_id TEXT PRIMARY KEY,
       lot_id TEXT NOT NULL,
       device_variant TEXT NOT NULL CHECK (device_variant IN ('CMOS_A','CMOS_B','CMOS_C')),
       device_family TEXT NOT NULL DEFAULT 'DIGITAL_CMOS',
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
   );
   ```
2. **`measurements` Table:**
   ```sql
   CREATE TABLE measurements (
       measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
       component_id TEXT NOT NULL,
       epoch_h INTEGER NOT NULL CHECK (epoch_h IN (0,24,96,168)),
       IDDQ REAL NOT NULL CHECK (IDDQ > 0),
       Input_Leakage_Current REAL NOT NULL CHECK (Input_Leakage_Current > 0),
       Active_Supply_Current REAL NOT NULL CHECK (Active_Supply_Current > 0),
       Propagation_Delay REAL NOT NULL CHECK (Propagation_Delay > 0),
       Output_Rise_Time REAL NOT NULL CHECK (Output_Rise_Time > 0),
       Output_Fall_Time REAL NOT NULL CHECK (Output_Fall_Time > 0),
       measured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       source TEXT NOT NULL DEFAULT 'manual',
       UNIQUE(component_id, epoch_h),
       FOREIGN KEY(component_id) REFERENCES components(component_id)
   );
   ```
3. **`analysis_results` Table:**
   Stores computed inference verdicts (`PASS`, `MONITOR`, `REJECT`), primary parameters, and predicted 168h values for operational components.

---

## 10. Legacy, Demo & Archive Files

The repository isolates legacy prototypes in `data/_archive/` and preserves them without impacting production:

| Legacy File | Location | Historical Role | Current Status |
| :--- | :--- | :--- | :--- |
| `explainability_report.csv` | `data/_archive/` | Early 297-row mock explainability file | **DEPRECATED / ARCHIVED** |
| `fused_component_summary.csv` | `data/_archive/` | Early 297-row prototype fusion output | **DEPRECATED / ARCHIVED** |
| `modulea_component_summary.csv`| `data/_archive/` | Early 297-row Module A summary | **DEPRECATED / ARCHIVED** |
| `moduleb_component_summary.csv`| `data/_archive/` | Early 297-row Module B summary | **DEPRECATED / ARCHIVED** |
| `sih26170.db` | `backend/` | Empty legacy database from early scaffolding | **UNUSED** (`operational.db` is active) |
| `fusion.py` | `backend/fusions/` | Standalone prototype script for 297 rows | **REPLACED** by `data_loader.py` |
| `database.py` / `models.py` | `backend/` | Early SQLAlchemy models for `sih26170.db` | **REPLACED** by `operational_db.py` |

---

## 11. Authoritative vs. Derived Files Master Table

| File Name & Path | Authoritative? | Can Modify? | Consumed By | Architectural Purpose |
| :--- | :---: | :---: | :--- | :--- |
| `data/final/Fusion_Joined_Holdout.csv` | **YES** | **NO (FROZEN)** | `backend/data_loader.py` | Authoritative holdout ground truth |
| `data/final/ModuleA_Final_Holdout_*.csv` | **YES** | **NO (FROZEN)** | `backend/data_loader.py` | Multi-epoch screening evaluations |
| `data/final/ModuleB_Final_Holdout_Predictions.csv`| **YES** | **NO (FROZEN)** | `backend/data_loader.py` | 168h forecasts and P95 bounds |
| `data/final/*_Release_Manifest.json` | **YES** | **NO (FROZEN)** | `backend/main.py` | Release verification certificates |
| `data/reference/Device_Specs.csv` | **YES** | **NO (FROZEN)** | `data_loader.py`, `/system` | Physical datasheet maximum limits |
| `data/reference/Schema_Data_Dictionary.csv` | **YES** | **NO (FROZEN)** | `data_loader.py`, `/system` | Schema definitions and rules |
| `backend/operational.db` | Derived | **YES (R/W)** | `operational_routes.py` | Local operational data store |
| `backend/data_loader.py` | Code | YES | `backend/main.py` | In-memory indexing and scoring engine |
| `backend/main.py` | Code | YES | Frontend clients | Primary FastAPI REST server |
| `frontend/src/pages/*.jsx` | Code | YES | Web browsers | React UI views |

---

## 12. Reproducibility & Build Instructions

To reproduce and execute this project on a clean Windows machine:

### 1. Prerequisites
- Python 3.11+ (Python 3.13 tested)
- Node.js 20+ and npm
- Git

### 2. Backend Setup & Startup
```powershell
# Navigate to backend directory
cd C:\Users\admin\Desktop\sih26170\backend

# Install Python dependencies
pip install fastapi uvicorn pandas numpy scikit-learn

# Run the 12 automated integration tests
python test_integration.py

# Launch the FastAPI backend on port 8001
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

### 3. Frontend Setup & Startup
```powershell
# In a separate terminal, navigate to frontend directory
cd C:\Users\admin\Desktop\sih26170\frontend

# Install dependencies (use cmd.exe on Windows PowerShell if execution policies apply)
cmd.exe /c npm install

# Build the production bundle
cmd.exe /c npm run build

# Launch the Vite development server on port 5174
cmd.exe /c npm run dev -- --port 5174 --host
```

### 4. Verification
- Open `http://localhost:5174` in any web browser.
- Open `http://127.0.0.1:8001/docs` to inspect the Swagger API documentation.

---

## 13. Git & Repository Structure

### Recommended `.gitignore` Rules
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.joblib
*.npy

# Node & Frontend
node_modules/
dist/
dist-ssr/
*.local

# Databases & Runtime Logs
*.log
backend/operational.db-shm
backend/operational.db-wal
```

### Commit Guidelines
- **Commit:** Source code (`backend/*.py`, `frontend/src/**/*`), reference contracts (`data/reference/*`), release manifests (`*_Release_Manifest.json`), documentation (`docs/*`), and frozen benchmark CSVs (`data/final/*`).
- **Never Commit:** Operational database binaries containing test-floor data (`operational.db`), Node dependency directories (`node_modules`), or ephemeral Vite build artifacts (`dist`).

---

## 14. Troubleshooting & Known Engineering Issues

1. **Port Conflict on Port 8000 / 5173:**
   - *Cause:* The separate `Information_Environment` project or other services may occupy default ports `8000` and `5173`.
   - *Solution:* SIH26170 is explicitly configured to use port **8001** (FastAPI) and port **5174** (Vite).
2. **PowerShell Script Execution Policy Error on `npm`:**
   - *Cause:* Windows PowerShell restricts execution of un-signed scripts (`npm.ps1`).
   - *Solution:* Always invoke npm via `cmd.exe /c npm run dev` or `cmd.exe /c npm run build`.
3. **LightningCSS Pseudo-Element Minification Error:**
   - *Cause:* LightningCSS parser fails when CSS contains orphaned rules or spaces in pseudo-selectors.
   - *Solution:* Verified and resolved in `src/pages/ComponentDetail.css`. `cmd.exe /c npm run build` compiles with 0 errors.
4. **Windows Console Unicode `charmap` Encoding:**
   - *Cause:* Python printing non-ASCII characters (e.g., `≈`, `—`, `✓`) to the Windows CP1252 terminal.
   - *Solution:* All backend endpoints and scripts use explicit UTF-8 encoding or safe ASCII fallbacks.

---

## 15. Final "How Everything Connects" Summary

1. **Where does the data come from?**  
   The authoritative benchmark data originates in `incoming/chaitanya` as the frozen `SIH26170-FINAL-01` dataset ($N = 1,343$ holdout components across 18 whole lots).
2. **Which file processes it?**  
   `backend/data_loader.py` loads `data/final/Fusion_Joined_Holdout.csv`, caches it in memory, indexes components, and computes fused verdicts.
3. **Which model analyzes it?**  
   - **Module A:** Multi-group Mahalanobis & robust-z outlier scorer (`module_a_final01.joblib`).
   - **Module B:** Huber robust regressor predicting 168h relative drift with conformalized P95 bounds.
4. **Where is the result stored?**  
   Pre-computed benchmark results reside immutably in `data/final/Fusion_Joined_Holdout.csv`. New test-floor measurements are committed to SQLite `backend/operational.db`.
5. **Which API exposes it?**  
   FastAPI in `backend/main.py` exposes 18 REST endpoints on `http://127.0.0.1:8001`.
6. **Which frontend page displays it?**  
   The React application on `http://localhost:5174` renders results across 7 dedicated views: `Overview.jsx` (KPIs), `Analyze.jsx` (Search), `ComponentDetail.jsx` (Forensics & Charts), `Components.jsx` (Fleet Table), `Models.jsx` (Confusion Matrix & Evaluation), `Data.jsx` (Operational Wizard), and `System.jsx` (Architecture & Lineage).
