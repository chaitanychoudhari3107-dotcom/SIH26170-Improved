# SIH26170 — Revised Implementation Plan (FINAL Files)

Based on thorough inspection of all files in `incoming/nirmik/`, `incoming/riddhi/`, and `incoming/chaitanya/`.

---

## 1. Data Integration Map

### incoming/nirmik/ — Module B (Nirmik, FINAL01-RC2)

| File | Purpose | Module | Key Columns | Rows | Application Use | Replaces Existing? |
|------|---------|--------|-------------|------|-----------------|-------------------|
| `results/ModuleB_Final_Holdout_Predictions.csv` | **AUTHORITATIVE** Module B predictions for holdout | Module B output | 15 contract + 24 evidence cols (see below) | 1343 | **Primary data source**: served to frontend for Module B analysis | Yes — `data/ModuleB_Final_Holdout_Predictions.csv` (old had different schema) |
| `data/01_BUILD/ModuleB_Train.csv` | Training data split | Frozen benchmark | Wide-format measurements | N/A | **Reference/archive only** — never exposed in app | No existing equivalent |
| `data/02_CALIBRATE/ModuleB_Calibration.csv` | Calibration data split | Frozen benchmark | Wide-format measurements | N/A | **Reference/archive only** | No |
| `data/03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv` | Holdout input data (no 168h targets) | Frozen benchmark | Component IDs + 0h/24h predictors | 1343 | **Reference only** — DO NOT expose 168h targets | No |
| `data/REFERENCE/Device_Specs.csv` | Device specification limits | Reference | variant, parameter, spec_limit | 18 | Backend: spec limits for evidence display | Yes — `data/reference/Device_Specs.csv` |
| `data/REFERENCE/Schema_Data_Dictionary.csv` | Column definitions | Reference | column, type, unit, description | 27 | Models page: schema display | Yes — `data/reference/Schema_Data_Dictionary.csv` |
| `data/REFERENCE/Dataset_Version_Safe.json` | Dataset version metadata | Reference | dataset_id, status, rows, lots | 1 | Models/System pages | Yes — `data/reference/Dataset_Version_Safe.json` |
| `data/REFERENCE/ModuleB_Output_Contract.csv` | Contract column list | Reference | 15 column names | 1 header | Models page: contract display | Yes — `data/reference/ModuleB_Output_Contract.csv` |
| `models/FREEZE_RECEIPT.json` | Model freeze record | Frozen artifact | freeze timestamp, config digest | 1 | Models page: freeze date display | No |
| `RELEASE_MANIFEST.json` | Complete release metadata | Documentation | version, verification, decisions | 1 | Models/System pages | No |
| `moduleb/*.py` (17 files) | **Complete Module B Python package** | Module B engine | Callable predict/contract/serve code | — | **Can be used as live inference engine** | Yes — fills empty `backend/modules/` |
| `docs/*.md` (14 files) | Documentation | Reference | — | — | Archive only | No |
| `scripts/*.py` (17 files) | Pipeline scripts | Reference | — | — | Archive only | No |
| `tests/*.py` (7 files) | Test suite | Testing | — | — | CI/CD only | No |
| `requirements.txt` | Python dependencies | Build | — | — | Backend requirements | No |

#### Module B Output Contract (15 contract + 24 evidence columns)

**Contract columns** (fixed, ordered):
```
component_id
predicted_IDDQ_168h
predicted_Input_Leakage_Current_168h
predicted_Active_Supply_Current_168h
predicted_Propagation_Delay_168h
predicted_Output_Rise_Time_168h
predicted_Output_Fall_Time_168h
module_b_p95_IDDQ_168h
module_b_p95_Input_Leakage_Current_168h
module_b_p95_Active_Supply_Current_168h
module_b_p95_Propagation_Delay_168h
module_b_p95_Output_Rise_Time_168h
module_b_p95_Output_Fall_Time_168h
module_b_primary_parameter
module_b_reason_codes
```

**Evidence columns** (additive, 4 per parameter × 6 parameters = 24):
```
evidence_{PARAM}_limit                    — spec limit (NaN if none)
evidence_{PARAM}_pred_frac_of_limit       — predicted / limit
evidence_{PARAM}_pred_rel_delta_from_24h  — (pred - 24h) / 24h
evidence_{PARAM}_lot_rel_dev_24h          — 24h / lot_median_24h - 1
```

> [!IMPORTANT]
> **Module B emits NO disposition column.** Per decision D1, the final PASS/MONITOR/REJECT belongs to fusion. There is no `module_b_disposition`, `disposition_B`, or `risk_B` field. This is a critical difference from the existing demo data which had `disposition_B` and `risk_B`.

**Module B reason codes** (pipe-delimited):
- `B_HIGH_FORECAST_DRIFT` — drift z ≥ 3.0 on primary parameter
- `B_WIDE_ENVELOPE` — p95 envelope width ≥ 90th percentile among same-primary components
- `B_LOT_OUTLIER_24H` — 24h lot z ≥ 3.0 on primary parameter
- `B_FORECAST_EXCEEDS_LIMIT` — point forecast ≥ spec limit
- `B_ENVELOPE_REACHES_LIMIT` — envelope ≥ limit but point forecast below
- `B_NO_EARLY_SIGNAL` — qualifies existing flags with low early signal
- Empty string = no flags fired

---

### incoming/riddhi/ — Module A (Riddhi, FINAL01-RC1)

| File | Purpose | Module | Key Columns | Rows | Application Use | Replaces? |
|------|---------|--------|-------------|------|-----------------|-----------|
| `prediction/ModuleA_Final_Holdout_0h.csv` | Module A scores at 0h epoch | Module A output | 13 columns (see below) | 1343 | Serve for 0h analysis (early epoch) | No direct equivalent |
| `prediction/ModuleA_Final_Holdout_24h.csv` | Module A scores at 24h epoch | Module A output | 13 columns | 1343 | Serve for 24h analysis | No direct equivalent |
| `prediction/ModuleA_Final_Holdout_96h.csv` | Module A scores at 96h epoch | Module A output | 13 columns | 1343 | Serve for 96h analysis | No direct equivalent |
| `prediction/ModuleA_Final_Holdout_168h.csv` | **AUTHORITATIVE** Module A at full trajectory | Module A output | 13 columns | 1343 | **Primary Module A display** | Yes — `data/modulea_component_summary.csv` |
| `results/15_fusion_joined_holdout.csv` | **AUTHORITATIVE** pre-joined Module A + Module B | Fusion | 45 columns (A+B+evidence) | 1343 | **Primary unified analysis source** | Yes — `data/fused_component_summary.csv` and `data/explainability_report.csv` |
| `results/15_fusion_dryrun.csv` | Fusion integrity checks | Fusion | check, status, detail | 9 | Verification evidence | No |
| `results/15_fusion_dryrun.json` | Fusion integrity metadata | Fusion | checks, agreement stats | 1 | System page: integration status | No |
| `models/module_a_final01.joblib` | **Frozen Module A model artifact** | Module A engine | Serialized scikit-learn model | 1 | **Can be used for live inference** | No direct equivalent |
| `models/FREEZE_RECEIPT.json` | Module A freeze record | Frozen artifact | freeze timestamp | 1 | Models page | No |
| `modulea/*.py` (16 files) | **Complete Module A Python package** | Module A engine | Callable predict/score/contract code | — | **Can be used as live inference engine** | Yes — fills empty `backend/modules/` |
| `results/*.csv/*.json` (~40 files) | Validation/analysis results | Reference | Metrics, curves, diagnostics | — | Archive/Models page subset | No |
| `docs/*.md` (13 files) | Documentation | Reference | — | — | Archive only | No |
| `scripts/*.py` (20 files) | Pipeline scripts | Reference | — | — | Archive only | No |
| `tests/*.py` (12 files) | Test suite | Testing | — | — | CI/CD only | No |
| `packets/` | Team handoff packets (Anushka, Tanisha) | Reference | Evidence, domain files | — | Archive only | No |

#### Module A Output Contract (13 columns per epoch)

**Contract fields** (5, ordered, fixed):
```
component_id
module_a_score           — [0, 1] monotone, [0.0, 0.90) = statistical, [0.90, 1.0] = confirmed limit violation
module_a_disposition     — PASS | MONITOR (never REJECT — fusion owns that)
module_a_primary_parameter   — strongest parameter (only populated for MONITOR)
module_a_reason_codes        — pipe-delimited (see below)
```

**Diagnostic fields** (8, additive):
```
module_a_evidence_tier       — PASS | MONITOR | CONFIRMED
module_a_attribution_margin  — gap between primary and runner-up parameter
statistical_score            — raw statistical rank score before composition
spec_exceedance_ratio        — how far past spec limit (only for CONFIRMED)
scored_epoch_h               — 0 | 24 | 96 | 168
analysis_status              — PARTIAL_1_EPOCH | PARTIAL_2_EPOCH | PARTIAL_3_EPOCH | COMPLETE_4_EPOCH
model_version                — ModuleA-FINAL01
dataset_id                   — SIH26170-FINAL-01
```

> [!IMPORTANT]
> **Module A emits PASS and MONITOR only, never REJECT.** This differs from the existing demo data which had `disposition_A` with PASS/MONITOR/REJECT values. The existing `risk_A` field also does not exist in the FINAL data — Module A has `module_a_score` (0-1 range) instead.

**Module A reason codes** (pipe-delimited):
- `A_STATIC_LIMIT_EXCEEDED:{parameter}` — datasheet limit violation
- `A_LOT_RELATIVE_DEVIATION` — deviates from own lot
- `A_OVERALL_EXTREME` — extreme vs variant reference
- `A_ELECTRICAL` — electrical-group deviation
- `A_TEMPORAL` — change-over-time deviation
- `A_TIMING` — timing-group deviation
- `A_OK` — no evidence above threshold

---

### incoming/chaitanya/ — Team Bundle (Integration + Domain + Reference)

| File | Purpose | Module | Key Columns | Rows | Application Use | Replaces? |
|------|---------|--------|-------------|------|-----------------|-----------|
| `anushka/Integration_Contract_Safe.json` | Integration contract | Fusion | join_key, field lists, fusion rules | 1 | Backend: fusion logic reference | Yes — `data/reference/Integration_Contract_Safe.json` |
| `anushka/ModuleA_Output_Contract.csv` | Module A contract header | Reference | 5 column names | 1 header | Models page | Yes |
| `anushka/ModuleB_Output_Contract.csv` | Module B contract header | Reference | 15 column names | 1 header | Models page | Yes |
| `anushka/Fusion_Output_Contract.csv` | Fusion contract header | Reference | 9 column names | 1 header | Models page | Yes |
| `anushka/Dataset_Version_Safe.json` | Dataset version info | Reference | dataset_id, rows, lots | 1 | System page | Yes |
| `anushka/Device_Specs.csv` | Device specifications | Reference | variant, parameter, limits | 18 | Spec display | Yes |
| `anushka/Schema_Data_Dictionary.csv` | Data dictionary | Reference | column definitions | 27 | Models page | Yes |
| `anushka/Safe_Lot_Split_Manifest.csv` | Lot split assignments | Reference | lot, variant, split | — | Reference only | Yes |
| `anushka/Integration_Sample_60_TrainOnly.csv` | 60-row integration sample | Demo | wide-format measurements | 60 | **Demo/test only** — not production data | Yes |
| `anushka/FINAL_APPROVAL.md` | Dataset approval record | Reference | — | — | Archive | Yes |
| `anushka/operational_demo/*` | Operational layer spec | Reference | API contract, DB schema, templates | — | Backend: operational routes reference | Yes — `data/operational/*` |
| `tanisha/Device_Specs.csv` | Domain-verified specs | Reference | Duplicate of Anushka's | — | Cross-reference only | — |
| `tanisha/Schema_Data_Dictionary.csv` | Domain-verified dictionary | Reference | Same as Anushka's | — | Cross-reference only | — |
| `tanisha/Dataset_Version_Safe.json` | Domain copy | Reference | Same as others | — | Cross-reference only | — |

---

## 2. Critical Differences: Existing Demo vs FINAL Files

| Aspect | Existing Demo (`data/`) | FINAL Files (`incoming/`) |
|--------|------------------------|--------------------------|
| **Component count** | 297 | **1343** (holdout set) |
| **Module A columns** | `disposition_A`, `risk_A`, `driving_parameter`, `confidence`, `reason_code`, `reason_text` | `module_a_score`, `module_a_disposition`, `module_a_primary_parameter`, `module_a_reason_codes`, `module_a_evidence_tier`, + 7 diagnostic fields |
| **Module A dispositions** | PASS / MONITOR / REJECT | **PASS / MONITOR only** (no REJECT — fusion owns REJECT) |
| **Module B columns** | `disposition_B`, `risk_B`, `driving_headroom_frac`, `n_params_predicted`, `confidence`, `extrapolation_flag` | 15 contract cols + 24 evidence cols. **No disposition_B**, no risk_B, no confidence, no extrapolation_flag |
| **Module B detail** | Per-parameter long format (`moduleb_predictions_long.csv`) with 1782 rows | Per-parameter evidence embedded in holdout predictions (24 evidence columns) |
| **Fusion** | Custom script producing `fused_component_summary.csv` + `explainability_report.csv` | **Pre-joined `15_fusion_joined_holdout.csv`** with 45 columns |
| **Module source code** | Empty `backend/modules/` directory | Complete `modulea/` (16 files) and `moduleb/` (17 files) Python packages with frozen `.joblib` artifacts |
| **Dataset** | SIH26170-MOCK-02 (297 components) | **SIH26170-FINAL-01** (5400 total, 1343 holdout) |

> [!WARNING]
> The existing `data/` files are based on a different, earlier demo dataset (297 components, SIH26170-MOCK-02). The column schemas are incompatible with the FINAL files. Every existing CSV in `data/` except the reference files must be treated as **demo artifacts** to be replaced.

---

## 3. Files to Retain vs Deprecate

### ✅ Files to RETAIN (existing backend code)

| File | Reason |
|------|--------|
| [main.py](file:///C:/Users/admin/Desktop/sih26170/backend/main.py) | Application entry point — will be **modified** |
| [operational/operational_routes.py](file:///C:/Users/admin/Desktop/sih26170/backend/operational/operational_routes.py) | Production operational API — **keep and extend** |
| [operational/operational_db.py](file:///C:/Users/admin/Desktop/sih26170/backend/operational/operational_db.py) | DB connection helper — **keep** |
| [operational/Operational_DB_Schema.sql](file:///C:/Users/admin/Desktop/sih26170/backend/operational/Operational_DB_Schema.sql) | Schema — **keep unchanged** |
| [operational/Operational_API_Contract.json](file:///C:/Users/admin/Desktop/sih26170/backend/operational/Operational_API_Contract.json) | API contract — **keep unchanged** |
| `operational.db` | Existing operational data — **keep** |

### ⚠️ Files to DEPRECATE (move to `_archive/` — not delete)

| File | Reason |
|------|--------|
| `data/explainability_report.csv` | 297-row demo data, wrong column schema |
| `data/modulea_component_summary.csv` | 297-row demo, wrong columns (`disposition_A`, `risk_A`) |
| `data/moduleb_component_summary.csv` | 297-row demo, wrong columns (`disposition_B`, `risk_B`) |
| `data/moduleb_predictions_long.csv` | 297×6 demo long-format, superseded by evidence columns |
| `data/fused_component_summary.csv` | 297-row demo fusion output |
| `data/ModuleB_Final_Holdout_Predictions.csv` | Old holdout file from MOCK-02 dataset |
| `backend/models.py` | Legacy SQLAlchemy model (5 fields only) |
| `backend/schemas.py` | Legacy Pydantic schema |
| `backend/database.py` | Legacy DB engine for `sih26170.db` |
| `backend/sih26170.db` | Legacy demo database |
| `backend/fusions/fusion.py` | Old fusion script (wrong column names) |
| `backend/explainability/explainability_report.py` | Old explainability script (wrong columns) |

### 🔒 Files that are FROZEN and must NEVER be modified

| File | Reason |
|------|--------|
| `incoming/nirmik/.../models/FREEZE_RECEIPT.json` | Module B freeze record |
| `incoming/riddhi/.../models/module_a_final01.joblib` | Module A frozen model |
| `incoming/riddhi/.../models/FREEZE_RECEIPT.json` | Module A freeze record |
| `incoming/nirmik/.../data/03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv` | Holdout input (no targets) |
| All `SHA256SUMS.txt` files | Integrity verification |

---

## 4. Final Data Architecture

```
data/
├── final/                                          # AUTHORITATIVE analysis data
│   ├── ModuleA_Final_Holdout_168h.csv             # Module A at 168h (1343 rows × 13 cols)
│   ├── ModuleA_Final_Holdout_24h.csv              # Module A at 24h (for epoch comparison)
│   ├── ModuleA_Final_Holdout_0h.csv               # Module A at 0h
│   ├── ModuleA_Final_Holdout_96h.csv              # Module A at 96h
│   ├── ModuleB_Final_Holdout_Predictions.csv      # Module B predictions (1343 × 39 cols)
│   └── Fusion_Joined_Holdout.csv                  # Pre-joined A+B (1343 × 45 cols)
├── reference/                                      # Contracts, specs, dictionary
│   ├── Device_Specs.csv
│   ├── Schema_Data_Dictionary.csv
│   ├── Dataset_Version_Safe.json
│   ├── ModuleA_Output_Contract.csv
│   ├── ModuleB_Output_Contract.csv
│   ├── Fusion_Output_Contract.csv
│   ├── Integration_Contract_Safe.json
│   ├── Safe_Lot_Split_Manifest.csv
│   └── FINAL_APPROVAL.md
├── operational/                                    # Operational layer docs (unchanged)
│   ├── README_Operational_Layer.md
│   ├── Operational_Input_Example_12Rows.csv
│   └── Operational_Measurement_Input_Template.csv
└── _archive/                                       # Deprecated demo files (preserved)
    ├── explainability_report.csv
    ├── modulea_component_summary.csv
    ├── moduleb_component_summary.csv
    ├── moduleb_predictions_long.csv
    └── fused_component_summary.csv
```

---

## 5. Backend Architecture

### Data Loading (startup)

Load the following CSVs once into memory at FastAPI startup:

1. **`Fusion_Joined_Holdout.csv`** (1343 × 45) — the primary data source for component analysis
2. **`ModuleA_Final_Holdout_168h.csv`** (1343 × 13) — Module A detailed view
3. **`ModuleB_Final_Holdout_Predictions.csv`** (1343 × 39) — Module B detailed view with evidence
4. **`Device_Specs.csv`** — spec limits for display
5. **`Schema_Data_Dictionary.csv`** — for Models page

### API Endpoints

| Method | Path | Purpose | Source |
|--------|------|---------|--------|
| `GET` | `/` | Health check | Existing |
| `GET` | `/api/analysis/search?q={query}&type={component\|lot}` | Search components | Fusion CSV |
| `GET` | `/api/analysis/{component_id}` | **Full component analysis** — A + B + evidence | Fusion + ModuleB CSVs |
| `GET` | `/api/analysis/{component_id}/module-a` | Module A detail (all epochs) | ModuleA CSVs (0h, 24h, 96h, 168h) |
| `GET` | `/api/analysis/{component_id}/module-b` | Module B predictions + evidence | ModuleB CSV |
| `GET` | `/api/analysis/summary` | Aggregate counts (total, PASS, MONITOR, by variant) | Fusion CSV |
| `GET` | `/api/components` | Paginated component list with filters | Fusion CSV |
| `GET` | `/api/models/info` | Module A/B metadata, versions, contracts | Manifest JSONs |
| `GET` | `/api/system/status` | API/DB/data health | Live checks |
| `GET` | `/api/reference/specs` | Device specifications | Device_Specs.csv |
| `GET` | `/api/reference/dictionary` | Data dictionary | Schema_Data_Dictionary.csv |
| `POST` | `/api/measurements` | Add operational measurement | **Existing** |
| `GET` | `/api/components/{id}` | Operational component detail | **Existing** |
| `GET` | `/api/components/{id}/trajectory` | Operational trajectory | **Existing** |
| `GET` | `/api/dashboard/summary` | Operational summary | **Existing** |

### Component Analysis Response Shape

For `GET /api/analysis/{component_id}`:

```json
{
  "component_id": "C00158",
  "module_a": {
    "score": 0.6646,
    "disposition": "PASS",
    "primary_parameter": null,
    "reason_codes": "A_OK",
    "evidence_tier": "PASS",
    "attribution_margin": null,
    "statistical_score": 0.7384,
    "spec_exceedance_ratio": null,
    "analysis_status": "COMPLETE_4_EPOCH",
    "model_version": "ModuleA-FINAL01",
    "epochs": { "0": {...}, "24": {...}, "96": {...}, "168": {...} }
  },
  "module_b": {
    "predictions": {
      "IDDQ": { "predicted_168h": 1.7538, "p95_168h": 1.8453 },
      "Input_Leakage_Current": { "predicted_168h": 0.01676, "p95_168h": 0.01807 },
      ...
    },
    "primary_parameter": "Output_Rise_Time",
    "reason_codes": "",
    "evidence": {
      "IDDQ": { "limit": 40.0, "pred_frac_of_limit": 0.0438, "pred_rel_delta_from_24h": 0.0229, "lot_rel_dev_24h": 0.0647 },
      ...
    }
  },
  "fusion": {
    "b_evidence_status": "NOT_APPLICABLE"
  }
}
```

> [!NOTE]
> The FINAL fusion joined file does NOT contain a `final_decision` / `final_disposition` column. The `15_fusion_joined_holdout.csv` is a JOIN, not a fusion output. The existing backend's `fuse_decision()` logic must be reimplemented using the FINAL column names. However, Module A never emits REJECT, and Module B emits no disposition at all. The fusion logic needs to be:
> - Module A MONITOR with `evidence_tier == "CONFIRMED"` → candidate for REJECT (spec limit exceeded)
> - Module A MONITOR → MONITOR
> - Module B reason codes firing (any `B_FORECAST_EXCEEDS_LIMIT`) → MONITOR/REJECT depending on severity
> - Both clear → PASS
> 
> **Decision required from you**: The existing `fusions/fusion.py` used `disposition_A REJECT → REJECT` and `disposition_B REJECT → REJECT`, but Module A never emits REJECT and Module B has no disposition. How should we determine a final decision? Options:
> - **(a)** Module A `CONFIRMED` tier → REJECT, Module A MONITOR → MONITOR, B flags → MONITOR, else PASS
> - **(b)** Only Module A `CONFIRMED` + B `FORECAST_EXCEEDS_LIMIT` → REJECT
> - **(c)** Use `module_a_disposition` and B reason codes to derive final decision with a clearly documented rule set
> - **(d)** The fusion joined file already has the data — just display Module A's disposition and Module B's evidence, without inventing a combined decision

---

## 6. Frontend Architecture

Same page structure as previous plan, but adapted to FINAL data contracts:

### Pages

1. **Overview** — System status, counts (1343 holdout components), quick search, recent analyses
2. **Analyze** — Search → ComponentDetail
3. **ComponentDetail** (`/analyze/:componentId`)
   - Component header with Module A disposition badge
   - **Module A**: score (0-1 bar), disposition, evidence tier, reason codes, primary parameter, epoch progression (0h→24h→96h→168h)
   - **Module B**: 6 parameter cards with predicted 168h, p95 envelope, evidence (limit fraction, predicted drift, lot relative deviation). Parameter selector for drill-down
   - **Fusion/Evidence**: combined view with reason codes from both, `b_evidence_status`
   - **"Why?" section**: structured explanation based on actual codes
4. **Components** — Data table of 1343 components, filterable by disposition/variant/lot
5. **Data** — Operational measurement management (Add Record wizard, View Records)
6. **Models** — Module A/B metadata, versions, contracts, freeze dates
7. **System** — API/DB/data health, dataset version

### New Dependencies

```
react-router-dom    — routing
lucide-react        — icons
recharts            — parameter charts (single-parameter only)
```

---

## 7. Database / Operational-Data Design

**No change** to the operational database schema (`operational.db`). The three tables remain:
- `components` — operational component registry
- `measurements` — operational measurements (separate from benchmark)
- `analysis_results` — placeholder for future live analysis results

**Separation rule**: All FINAL/benchmark data is served from CSVs loaded in memory. Operational records go to `operational.db`. The frozen benchmark is never modified by user actions.

---

## 8–10. Module Integration Flows

### Module A Integration Flow
```
Frontend search → API /api/analysis/{id} → Load from ModuleA CSVs (4 epochs)
→ Return: score, disposition (PASS|MONITOR), evidence_tier, reason_codes
→ Frontend displays: score bar, tier badge, reason code breakdown, epoch progression
```

### Module B Integration Flow  
```
Frontend ComponentDetail → API /api/analysis/{id}/module-b → Load from ModuleB CSV
→ Return: 6 predictions + 6 p95 envelopes + 24 evidence values + primary_parameter + reason_codes
→ Frontend displays: per-parameter cards, evidence details, reason code flags
```

### Fusion/Combined Flow
```
Frontend ComponentDetail → API /api/analysis/{id} → Load from Fusion_Joined CSV
→ Return: merged A+B data, b_evidence_status
→ Frontend: combined summary panel, evidence from both modules, explanation
```

---

## 11–12. Component Search & Add Record Flows

### Component Search
```
User types ID/lot → API /api/analysis/search?q=... 
→ Fuzzy/prefix match against 1343 holdout component_ids
→ Results with disposition badges → Click → ComponentDetail page
```

### Add Record
```
Step 1: Component ID, Lot ID, Device Variant
Step 2: Epoch (0 | 24 | 96 | 168)
Step 3: Six measurements (IDDQ, Input_Leakage_Current, Active_Supply_Current, Propagation_Delay, Output_Rise_Time, Output_Fall_Time)
Step 4: Validation preview (all existing backend rules preserved)
Step 5: Confirm → POST /api/measurements → operational.db only
```

---

## 13. Verification Plan

### Automated
- Backend: all endpoints return correct shapes against known component IDs
- Frontend: `npm run build` succeeds
- Module A holdout row count verified = 1343
- Module B holdout row count verified = 1343
- Fusion join verified = 1343 (all pass, no missing)

### Manual
1. Search component `C00158` — verify Module A shows PASS, score=0.6646
2. Module B shows 6 predictions, primary=Output_Rise_Time
3. Evidence columns populate correctly
4. Add operational record → verify stored in operational.db
5. Operational record does NOT appear in analysis/holdout data

---

## 14. Deployment Plan

1. Copy FINAL files to `data/final/` and `data/reference/` (preserve originals in `incoming/`)
2. Move old demo files to `data/_archive/`
3. Install Module A/B Python packages into `backend/modules/`
4. Update `main.py` to load FINAL CSVs and serve new endpoints
5. Restructure frontend from monolithic App.jsx to multi-page app
6. Install frontend dependencies (react-router-dom, lucide-react, recharts)
7. Test full flow end-to-end

---

## 15. Remaining Decisions Required

> [!IMPORTANT]
> **Decision 1: Final Fusion Disposition Logic**
> 
> The FINAL data has NO pre-computed `final_decision` column. Module A emits only PASS/MONITOR. Module B emits no disposition. How should the application determine a combined decision?
> 
> Options:
> - **(a)** `evidence_tier == CONFIRMED` → REJECT; `disposition == MONITOR` → MONITOR; else PASS
> - **(b)** Use Module A disposition as the final decision (since Module B explicitly defers to fusion)
> - **(c)** Implement new fusion rules based on Module A disposition + Module B reason codes
> - **(d)** Display both modules' outputs without computing a single final decision — let the user interpret

> [!IMPORTANT]
> **Decision 2: Module A/B Live Inference**
> 
> The incoming packages contain complete Python code + frozen `.joblib` models. For operationally-added records:
> - **(a)** Run live Module A inference on operational records when sufficient data exists — **technically possible but complex**
> - **(b)** Show operational records with "Pending analysis" status — simpler, safer
> - **(c)** Phase 1 = (b), Phase 2 = (a)

> [!NOTE]
> **Decision 3: Module A Multi-Epoch Display**
> 
> Module A provides holdout predictions at 4 epochs (0h, 24h, 96h, 168h). Should the ComponentDetail page:
> - **(a)** Show only the 168h (final) result with a note about earlier epochs
> - **(b)** Show an epoch progression view (0h→168h) demonstrating how the score evolves
> - **(c)** Show 168h by default with an expandable epoch history
> 
> I recommend **(c)** — shows 168h primary, with expandable epoch progression.

> [!NOTE]
> **Confirmed Non-Issues**
> - Module A and Module B join cleanly on `component_id` — 1343 rows on both sides, zero missing
> - Both modules reference the same `SIH26170-FINAL-01` dataset
> - No column name collisions between Module A and Module B contract columns
