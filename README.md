# SIH26170 — burn-in screening research prototype

A React/FastAPI application for exploring the delivered synthetic semiconductor benchmark and running a separate lot-screening workspace.

## What works

- Synthetic benchmark explorer: 1,343 holdout components, 18 lots; real 0/24/96/168h observations, forecast comparison, consistent fused verdicts.
- CSV validation and atomic imports; explicit expected lot size; immutable measurements; identical reimports skipped.
- Whole-lot Module A inference at 0/24/96/168h, Module B forecasts from 0/24h only. Minimum 30 components. Later runs reuse the original forecast.
- Distinct observed REJECT, forecast HOLD, MONITOR and early PROVISIONAL_PASS results. Any observed historical specification breach remains a rejection.
- Append-only review decisions, full evidence JSON and summary CSV exports, artifact/input hashes.
- Public read-only mode by default; shared operator token for protected access; payload limits, bounded literal search, readiness checks.

## Scientific limits — read before interpreting results

This is a research prototype using synthetic data, not a production qualification system. No zero-false-positive or zero-false-negative claim is made.

The delivered Module A artifact is used unchanged, with the declared serving lot manifest supplied at prediction time. Its rank cutoff is 0.9395405078597341; the confirmed-breach score floor is 0.900. These are different quantities.

The original Module B fitted artifact was missing. The operational B artifact was rebuilt using **only the delivered training and calibration partitions**, with REHEARSAL status. Historical benchmark B metrics belong to the original delivered predictions and **do not validate the rebuilt runtime**. Bounds are not guaranteed to provide 95% coverage. See `data/runtime/runtime_manifest.json` for provenance.

A forecast crossing a specification is a HOLD, not an observed failure. Static limits are applied only where supplied in `data/reference/Device_Specs.csv`; missing limits stay missing. All current parameters use µA; timing uses ns. Review approval does not certify a part or alter the model output. The shared operator credential does not identify individual reviewers.

## Local setup

Requires Python 3.12 and Node 22.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001 in your browser. For frontend development run `npm run dev` inside frontend; Vite proxies `/api` to port 8001.

The verified runtime artifacts are included; rebuilding is not required. To reproduce the rehearsal B fit from the archived sources: `python scripts/build_runtime.py`. This changes the runtime artifact and must be validated again before use.

## Enable protected operational work

Set environment variables **before starting the backend**. Choose a long random key. Never commit it or put it in VITE variables.

PowerShell:
```powershell
$env:SIH26170_OPERATOR_KEY="your-long-random-secret"
$env:SIH26170_DATABASE_PATH="C:\sih-data\operational.db"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Bash:
```bash
export SIH26170_OPERATOR_KEY='your-long-random-secret'
export SIH26170_DATABASE_PATH='/absolute/persistent/path/operational.db'
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Open **Data / Lot screening workspace** and enter the key. The browser keeps the key in memory only; refresh or Lock clears access. Server restart with a changed key revokes the old key.

`SIH26170_ENABLE_DEMO_WRITES=1` is an explicitly unauthenticated local demo mode. Do not enable it on an internet-facing instance. With neither setting, reads remain available and all writes are disabled.

## Try the complete workflow

1. Download the 24h synthetic fixture from the workspace. Set lot `DEMO_A`, variant `CMOS_A`, expected components **78**, measurements through **24h**.
2. Select the CSV, Validate, then Import. Validation rolls back; Import commits the lot atomically.
3. Analyze 24h and inspect a component's measurements, forecast and reason.
4. Download and import the corresponding 168h fixture with the same declaration and epoch **168h**.
5. Analyze 168h. The 24h forecast is reused; errors against observed 168h values are now visible.
6. Record a review with a reason and export the JSON evidence or CSV summary.

Fixtures are renamed training examples, useful for checking the workflow but not model evaluation. Partial imports are allowed; analysis requires exactly the declared complete lot and all preceding epochs. The server rejects future columns, labels, mixed variants/lots, nonfinite/negative measurements, duplicate IDs and conflicting reimports. Corrections to immutable records need a separately designed, audited revision workflow; do not edit the database by hand.

## Checks

```bash
# Bash
PYTHONPATH=backend python -m unittest backend.test_integration backend.test_operational -v
# PowerShell: $env:PYTHONPATH="backend"; python -m unittest backend.test_integration backend.test_operational -v
cd frontend
npm run build
npm run lint
```

Tests cover benchmark regressions, protected access, validation rollback, import conflicts, incomplete lots, invalid data, 24h-to-168h analysis, immutable forecast reuse, reviews and exports. GitHub Actions runs these checks on pushes and pull requests.

## Deploy

`Dockerfile` builds the frontend from source and bundles the model artifacts. `render.yaml` defines a **read-only demo**. For an existing Render Python service, either create a Docker service from the repository or set Python 3.12, Node 22, build `pip install -r requirements.txt && cd frontend && npm ci && npm run build`, start `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.

Configure `/api/health` as the readiness endpoint. For operational imports, configure the operator key and mount persistent storage, then set `SIH26170_DATABASE_PATH` to a file inside that mount. The default SQLite file on ephemeral hosting does **not** survive instance replacement. Back up the database using SQLite's backup API and test restoration. This implementation assumes one backend instance; use a server database and proper identity management before scaling to multiple instances.

Do not enable operational writes on an ephemeral public demo if records need to survive deployment. Never upload secrets, local databases, node_modules or .venv to GitHub.

## Remaining work before production

Obtain the original B artifact or independently validate the rebuilt model on untouched lots. Validate with real devices, production instrumentation and lot-disjoint data; measure precision, recall, false positives/negatives and interval coverage by variant/lot. Add individual accounts/roles, audited measurement corrections, durable database backups, deployment monitoring and an approved engineering release process. Browser/device acceptance and load testing remain deployment gates. The current operational policy and shared-key access are prototype choices, not production sign-off.
