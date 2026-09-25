# SIH26170 — Semiconductor Reliability Analysis Application
## Implementation & Verification Walkthrough

This document summarizes the end-to-end implementation of the SIH26170 semiconductor reliability analysis application prototype, following the finalized implementation plan.

---

## 1. Project Organization & Data Architecture

The repository data structure has been cleanly reorganized:

- **`data/final/`**: Contains the **authoritative 1,343-component final holdout dataset** (SIH26170-FINAL-01):
  - `Fusion_Joined_Holdout.csv`: Pre-joined Module A and Module B evaluation set (1,343 components, 45 contract & evidence columns).
  - `ModuleA_Final_Holdout_{0,24,96,168}h.csv`: Multi-epoch static classification outputs across burn-in milestones.
  - `ModuleB_Final_Holdout_Predictions.csv`: 168h prognostic drift predictions with 24 evidence metrics and uncertainty envelopes.
  - `ModuleB_Holdout.csv`: Baseline historical measurements at 0h and 24h, plus lot IDs and device variants.
  - `ModuleA_Release_Manifest.json` & `ModuleB_Release_Manifest.json`: Cryptographic freeze records, verification telemetry, and hyperparameters.
  - `Fusion_Dryrun.json`: 9-point integration contract verification audit record.
- **`data/reference/`**: Device specification limits (`Device_Specs.csv`), data dictionary (`Schema_Data_Dictionary.csv`), and contract schemas.
- **`data/_archive/`**: Deprecated 297-row mock demo files safely isolated.
- **`incoming/`**: Frozen release archives kept completely unmodified.

---

## 2. FastAPI Backend Architecture

The backend (`backend/`) was completely refactored to serve the authoritative final data:

1. **`backend/data_loader.py`**:
   - Ingests all final holdout datasets, device specifications, and release manifests into memory at startup.
   - Enriches components with metadata (`lot_id`, `device_variant`, `device_family`).
   - Implements automated, natural-language reliability explanation generation synthesizing Module A reason codes (`A_STATIC_LIMIT_EXCEEDED`, `A_LOT_RELATIVE_DEVIATION`, `A_ELECTRICAL`, etc.) and Module B warning flags (`B_HIGH_FORECAST_DRIFT`, `B_WIDE_ENVELOPE`, `B_LOT_OUTLIER_24H`, etc.).
   - Provides safe JSON scalar conversion (`_clean`) to prevent NaN/Infinity and NumPy serialization issues.
2. **`backend/main.py`**:
   - `GET /`: API health status.
   - `GET /api/analysis/search?q={query}`: Component and Lot ID search with live disposition and score badges.
   - `GET /api/analysis/{component_id}`: Comprehensive analysis payload (Module A contract, Module B predictions, 24 parameter evidence columns, fusion status, and historical measurements).
   - `GET /api/analysis/{component_id}/module-a`: Multi-epoch progression (0h, 24h, 96h, 168h).
   - `GET /api/analysis/{component_id}/module-b`: Detailed Module B prognosis and evidence vectors.
   - `GET /api/analysis/summary`: Fleet aggregate totals, dispositions, and evidence tiers.
   - `GET /api/components`: Paginated fleet browser with filtering by disposition and variant.
   - `GET /api/models/info`: Frozen model release manifests, hyperparameters, and integration audit results.
   - `GET /api/system/status`: Real-time subsystem health telemetry.
   - `GET /api/reference/specs` & `GET /api/reference/dictionary`: Specifications and data dictionary tables.
3. **`backend/operational/operational_routes.py`**:
   - Preserved and enhanced to support both flat and nested measurement schemas.
   - Completely isolates user-added operational records inside `operational.db`, strictly protecting frozen benchmark models from accidental retraining or data leakage.
   - Validates positive measurement values and enforces single-entry-per-epoch constraints (409 Conflict on duplicates).

---

## 3. Polished Vercel/Geist-Style Frontend

The frontend (`frontend/`) has been rebuilt with a clean, dark-first engineering design system:

- **Technology Stack**: React 19 + Vite 8 + React Router + Lucide Icons + Recharts.
- **Navigation Shell**: Fixed dark sidebar with icons for:
  - **Overview (`/`)**: System health badges, fleet KPI cards (Total, Pass, Monitor, Confirmed), quick search bar, and recent component activity table.
  - **Analyze (`/analyze`)**: Search-centric investigation interface with auto-focus search, immediate badge previews, and empty/error states.
  - **Component Detail (`/analyze/:componentId`)**:
    - Header with Component ID, Lot ID, Device Variant, Family, Disposition Badge, and Tier Badge.
    - **Module A Card**: Risk score progress bar, disposition, primary parameter, statistical rank score, and parsed reason code tags.
    - **Evidence & Explainability Card**: Fusion status badge, synthesized engineering assessment, and Module B indicator tags.
    - **Module B 168h Prognostic Drift**: 6 individual parameter cards (IDDQ, Input Leakage, Active Supply, Propagation Delay, Rise Time, Fall Time) displaying predicted 168h value, P95 envelope, datasheet limit, drift %, and lot dev %. Includes an inline Recharts bar chart comparing the P95 envelope against the spec limit with alert indicators.
    - **Historical Trajectory Table**: Chronological baseline readings (0h, 24h) across all six parameters.
  - **Components (`/components`)**: High-density interactive data table with server-side pagination and filters for disposition (`PASS`, `MONITOR`) and variants (`CMOS_A`, `CMOS_B`, `CMOS_C`).
  - **Operational Data (`/data`)**:
    - **View Records Tab**: Operational DB summary metrics, table of ingested measurements with timestamps, and registered component list.
    - **Add/Update Record Wizard**: 4-step guided form with real-time numeric validation (> 0), epoch selection (0h, 24h, 96h, 168h), review confirmation, and immediate success receipt with database commitment details.
  - **Models (`/models`)**: Comprehensive view of frozen Module A and Module B release manifests, test suite verification metrics (151 tests passed for Module A; 102 tests passed for Module B), known limitations, and 9-point integration dryrun checklist.
  - **System (`/system`)**: Real-time service health check, dataset information (`SIH26170-FINAL-01`), and database connectivity status.

---

## 4. Verification & Testing

### Automated Test Suite (`backend/test_integration.py`)
Run command: `python test_integration.py`
```
.........
----------------------------------------------------------------------
Ran 9 tests in 0.200s

OK
```
All 9 automated integration tests passed:
- `test_01_health_check`: Root endpoint healthy.
- `test_02_system_status`: Verifies all 1,343 fusion records, Module A records, and Module B records are loaded.
- `test_03_analysis_summary`: Validates fleet disposition totals match final holdout counts.
- `test_04_analysis_search`: Confirms prefix search returns structured component records.
- `test_05_component_detail_full`: Validates full analytical payload for component `C00158`.
- `test_06_components_pagination`: Validates 20-per-page pagination and data framing.
- `test_07_models_info`: Validates release metadata and `VERIFIED_PASS` integration status.
- `test_08_operational_measurement_lifecycle`: Validates measurement ingestion, negative input rejection, and duplicate conflict handling.
- `test_09_reference_endpoints`: Validates device specs and data dictionary endpoints.

### Frontend Production Build
Run command: `npm run build`
```
vite v8.3.0 building client environment for production...
✓ 2488 modules transformed.
dist/index.html                   0.47 kB │ gzip:   0.32 kB
dist/assets/index-Dlir3wSf.css   21.67 kB │ gzip:   4.18 kB
dist/assets/index-DIqqpESE.js   661.38 kB │ gzip: 197.04 kB
✓ built in 1.55s
```
Zero build errors or missing dependencies.

---

## 5. How to Run the Application

### Starting the Backend
```bash
cd sih26170/backend
python -m uvicorn main:app --reload --port 8000
```
API Documentation will be live at: `http://127.0.0.1:8000/docs`

### Starting the Frontend
```bash
cd sih26170/frontend
npm run dev
```
Application will be live at: `http://localhost:5173/`
