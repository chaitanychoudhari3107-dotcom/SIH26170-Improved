from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import math
import os
import sys
import sqlite3
from contextlib import closing

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Ensure backend directory is in sys.path whether executed from root or backend/
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Use our new pandas-based data loader
import data_loader
from operational.operational_routes import router as operational_router
from operational.operational_db import get_connection

from request_limits import RequestLimits
from operational.inference import runtime_status, clean
from operational.access import access_mode

app = FastAPI(title="SIH26170 Backend")
app.add_middleware(RequestLimits)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("SIH26170_CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep the operational routes intact at standard /api paths and /api/operational fallback
app.include_router(operational_router)

@app.get("/")
def health_check(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and FRONTEND_DIST.exists():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return {"status": "ok", "message": "SIH26170 Backend is running"}

@app.get("/api/analysis/search")
def search_components(q: str = Query(..., min_length=1, max_length=100)):
    results = data_loader.search_components(q)
    formatted = []
    for r in results:
        formatted.append({
            "component_id": r.get("component_id"),
            "disposition": r.get("module_a_disposition"),
            "fused_verdict": r.get("fused_verdict"),
            "module_a_disposition": r.get("module_a_disposition"),
            "evidence_tier": r.get("module_a_evidence_tier"),
            "module_a_evidence_tier": r.get("module_a_evidence_tier"),
            "score": r.get("module_a_score"),
            "module_a_score": r.get("module_a_score"),
            "primary_parameter": r.get("module_a_primary_parameter") or r.get("module_b_primary_parameter"),
            "module_b_primary_parameter": r.get("module_b_primary_parameter"),
        })
    return formatted

@app.get("/api/analysis/summary")
def get_summary():
    return data_loader.get_summary_counts()

@app.get("/api/analysis/{component_id}")
def get_analysis_detail(component_id: str):
    analysis = data_loader.get_component_analysis(component_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Component not found")
    return analysis

@app.get("/api/analysis/{component_id}/module-a")
def get_module_a_epochs(component_id: str):
    epochs_data = {}
    for epoch, df in data_loader.module_a_dfs.items():
        if component_id in df.index:
            epochs_data[epoch] = df.loc[component_id].to_dict()
        else:
            epochs_data[epoch] = None
            
    if all(v is None for v in epochs_data.values()):
        raise HTTPException(status_code=404, detail="Component not found in Module A data")
        
    return clean({"epochs": epochs_data})

@app.get("/api/analysis/{component_id}/module-b")
def get_module_b_detail(component_id: str):
    if component_id not in data_loader.module_b_df.index:
        raise HTTPException(status_code=404, detail="Component not found in Module B data")
    return clean(data_loader.module_b_df.loc[component_id].to_dict())

@app.get("/api/components")
def get_components_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    disposition: str = None,
    verdict: str = None,
    variant: str = None,
    lot: str = None,
    q: str | None = Query(None, max_length=100)
):
    df = data_loader.fusion_df
    
    if q:
        q = q.upper()
        mask = df["component_id"].str.upper().str.contains(q, na=False, regex=False)
        if "lot_id" in df.columns:
            mask = mask | df["lot_id"].str.upper().str.contains(q, na=False, regex=False)
        df = df[mask]
        
    if verdict:
        if "fused_verdict" in df.columns:
            df = df[df["fused_verdict"].str.upper() == verdict.upper()]
        elif "module_a_disposition" in df.columns:
            df = df[df["module_a_disposition"].str.upper() == verdict.upper()]
            
    if disposition:
        if "module_a_disposition" in df.columns:
            df = df[df["module_a_disposition"].str.upper() == disposition.upper()]
            
    if variant:
        var_col = "device_variant" if "device_variant" in df.columns else ("variant" if "variant" in df.columns else None)
        if var_col:
            df = df[df[var_col].str.upper() == variant.upper()]

    if lot:
        if "lot_id" in df.columns:
            df = df[df["lot_id"].str.upper() == lot.upper()]
            
    total = len(df)
    total_pages = math.ceil(total / per_page) if per_page > 0 else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    rows = df.iloc[start_idx:end_idx].to_dict(orient="records")
    paginated = []
    for r in rows:
        paginated.append({
            **r,
            "fused_verdict": r.get("fused_verdict", r.get("module_a_disposition", "PASS")),
            "disposition": r.get("module_a_disposition"),
            "evidence_tier": r.get("module_a_evidence_tier"),
            "score": r.get("module_a_score"),
            "primary_parameter": r.get("module_a_primary_parameter") or r.get("module_b_primary_parameter"),
            "variant": r.get("device_variant") or r.get("variant"),
        })
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "data": paginated
    }

@app.get("/api/models/info")
def get_models_info():
    return data_loader.get_models_info()

@app.get("/api/models/evaluation")
def get_models_evaluation():
    return data_loader.get_evaluation_metrics()

@app.get("/api/lots")
def get_lots():
    return data_loader.get_lots_summary()

@app.get("/api/pipeline/architecture")
def get_pipeline_architecture():
    return data_loader.get_pipeline_architecture()

@app.get("/api/system/status")
def system_status():
    ds_info = data_loader.dataset_version or {}
    data_ready = bool(len(data_loader.fusion_df) and len(data_loader.module_b_df)
                      and len(data_loader.module_a_dfs.get(168, [])))
    try:
        with closing(get_connection()) as connection:
            connection.execute("SELECT 1 FROM components LIMIT 1").fetchone()
        db_ok = True
    except (OSError, sqlite3.Error):
        db_ok = False
    return {
        "status": "ok" if data_ready and db_ok else "degraded",
        "api": "online",
        "api_status": "ok",
        "data_loaded": data_ready,
        "data_files_ok": data_ready,
        "db_status": "ok" if db_ok else "unavailable",
        "operational_db": "online" if db_ok else "unavailable",
        "operational_writes_enabled": access_mode() != "read_only",
        "runtime_ready": runtime_status()["ready"],
        "fusion_records": len(data_loader.fusion_df),
        "module_a_records_168h": len(data_loader.module_a_dfs.get(168, [])),
        "module_b_records": len(data_loader.module_b_df),
        "dataset_info": {
            "id": ds_info.get("dataset_id", "SIH26170-FINAL-01"),
            "status": ds_info.get("status", "AUTHORITATIVE_FROZEN_FINAL"),
            "rows": ds_info.get("total_rows", 5400),
            "lots": ds_info.get("total_lots", 72)
        },
        "environment": "research-prototype",
        "version": "1.0.0-final"
    }

@app.get("/api/health")
def readiness():
    state = system_status()
    ready = state['status'] == 'ok' and state['runtime_ready']
    return JSONResponse({'status': 'ok' if ready else 'degraded'}, status_code=200 if ready else 503)

@app.get("/api/reference/specs")
def get_device_specs():
    return data_loader.device_specs_df.to_dict(orient="records")

@app.get("/api/reference/dictionary")
def get_data_dictionary():
    return data_loader.schema_dictionary_df.to_dict(orient="records")

# Mount static assets if frontend production build exists
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(request: Request, full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
        
        target = (FRONTEND_DIST / full_path).resolve()
        if not target.is_relative_to(FRONTEND_DIST.resolve()):
            raise HTTPException(404, "Not Found")
        if target.exists() and target.is_file():
            return FileResponse(target)
        
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build not found")
