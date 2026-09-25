-- SIH 26170 operational/demo database schema
-- This database is separate from the frozen benchmark CSVs.
-- New operator data is inference/demo data and never modifies SIH26170-FINAL-01.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS components (
    component_id TEXT PRIMARY KEY,
    lot_id TEXT NOT NULL,
    device_variant TEXT NOT NULL CHECK (device_variant IN ('CMOS_A','CMOS_B','CMOS_C')),
    device_family TEXT NOT NULL DEFAULT 'DIGITAL_CMOS',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS measurements (
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

CREATE TABLE IF NOT EXISTS analysis_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id TEXT NOT NULL,
    analysis_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latest_epoch_h INTEGER NOT NULL,
    module_a_score REAL,
    module_a_disposition TEXT,
    module_a_primary_parameter TEXT,
    module_a_reason_codes TEXT,
    module_b_primary_parameter TEXT,
    module_b_reason_codes TEXT,
    predicted_IDDQ_168h REAL,
    predicted_Input_Leakage_Current_168h REAL,
    predicted_Active_Supply_Current_168h REAL,
    predicted_Propagation_Delay_168h REAL,
    predicted_Output_Rise_Time_168h REAL,
    predicted_Output_Fall_Time_168h REAL,
    p95_IDDQ_168h REAL,
    p95_Input_Leakage_Current_168h REAL,
    p95_Active_Supply_Current_168h REAL,
    p95_Propagation_Delay_168h REAL,
    p95_Output_Rise_Time_168h REAL,
    p95_Output_Fall_Time_168h REAL,
    final_disposition TEXT CHECK (final_disposition IN ('PASS','MONITOR','REJECT') OR final_disposition IS NULL),
    fusion_reason_codes TEXT,
    FOREIGN KEY(component_id) REFERENCES components(component_id)
);

CREATE INDEX IF NOT EXISTS idx_measurements_component_epoch
ON measurements(component_id, epoch_h);

CREATE INDEX IF NOT EXISTS idx_components_lot
ON components(lot_id);

CREATE INDEX IF NOT EXISTS idx_analysis_component_time
ON analysis_results(component_id, analysis_at);
