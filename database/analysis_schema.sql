-- Keiba Analyzer public portfolio schema
-- Synthetic/empty schema only. No collected race data is included.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS races (
    race_id          TEXT PRIMARY KEY,
    race_name        TEXT NOT NULL,
    race_date        TEXT NOT NULL,
    place            TEXT,
    course_type      TEXT,
    distance         INTEGER,
    weather          TEXT,
    track_condition  TEXT,
    CHECK (distance IS NULL OR distance > 0)
);

CREATE TABLE IF NOT EXISTS horses (
    horse_id    TEXT PRIMARY KEY,
    horse_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    race_id          TEXT NOT NULL,
    horse_id         TEXT NOT NULL,
    frame_number     INTEGER,
    horse_number     INTEGER,
    finish_position  INTEGER,
    popularity       INTEGER,
    odds             REAL,
    jockey_name      TEXT,
    carried_weight   REAL,
    passing_order    TEXT,
    last_3f          REAL,
    PRIMARY KEY (race_id, horse_id),
    FOREIGN KEY (race_id) REFERENCES races (race_id),
    FOREIGN KEY (horse_id) REFERENCES horses (horse_id),
    CHECK (frame_number IS NULL OR frame_number BETWEEN 1 AND 8),
    CHECK (horse_number IS NULL OR horse_number >= 1),
    CHECK (carried_weight IS NULL OR carried_weight > 0)
);

CREATE TABLE IF NOT EXISTS race_laps (
    race_id    TEXT NOT NULL,
    lap_index  INTEGER NOT NULL,
    distance   INTEGER NOT NULL,
    lap_time   REAL NOT NULL,
    PRIMARY KEY (race_id, lap_index),
    FOREIGN KEY (race_id) REFERENCES races (race_id),
    CHECK (lap_index >= 1),
    CHECK (distance > 0),
    CHECK (lap_time > 0)
);

CREATE TABLE IF NOT EXISTS horse_laps (
    race_id    TEXT NOT NULL,
    horse_id   TEXT NOT NULL,
    lap_index  INTEGER NOT NULL,
    distance   INTEGER NOT NULL,
    lap_time   REAL NOT NULL,
    PRIMARY KEY (race_id, horse_id, lap_index),
    FOREIGN KEY (race_id, horse_id) REFERENCES results (race_id, horse_id),
    CHECK (lap_index >= 1),
    CHECK (distance > 0),
    CHECK (lap_time > 0)
);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version_id       INTEGER PRIMARY KEY,
    version_name           TEXT NOT NULL UNIQUE,
    ability_logic_version  TEXT NOT NULL,
    track_logic_version    TEXT NOT NULL,
    pace_logic_version     TEXT NOT NULL,
    simulation_version     TEXT NOT NULL,
    created_at             TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    description            TEXT
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    analysis_run_id      INTEGER PRIMARY KEY,
    target_race_id       TEXT NOT NULL,
    model_version_id     INTEGER NOT NULL,
    data_cutoff_at       TEXT NOT NULL,
    input_snapshot_hash  TEXT NOT NULL,
    max_past_races       INTEGER NOT NULL DEFAULT 15,
    random_seed          INTEGER NOT NULL,
    status               TEXT NOT NULL DEFAULT 'CREATED',
    created_at           TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    completed_at         TEXT,
    FOREIGN KEY (target_race_id) REFERENCES races (race_id),
    FOREIGN KEY (model_version_id) REFERENCES model_versions (model_version_id),
    CHECK (max_past_races BETWEEN 1 AND 15),
    CHECK (
        status IN (
            'CREATED',
            'ABILITY_CALCULATED',
            'SCENARIO_CALCULATED',
            'SIMULATED',
            'COMPLETED',
            'INVALIDATED'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_target_created
    ON analysis_runs (target_race_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_entries (
    analysis_run_id  INTEGER NOT NULL,
    horse_id         TEXT NOT NULL,
    horse_number     INTEGER NOT NULL,
    frame_number     INTEGER,
    carried_weight   REAL NOT NULL,
    jockey_name      TEXT,
    scratched        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (analysis_run_id, horse_id),
    UNIQUE (analysis_run_id, horse_number),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id),
    FOREIGN KEY (horse_id) REFERENCES horses (horse_id),
    CHECK (horse_number >= 1),
    CHECK (frame_number IS NULL OR frame_number BETWEEN 1 AND 8),
    CHECK (carried_weight > 0),
    CHECK (scratched IN (0, 1))
);

CREATE TABLE IF NOT EXISTS analysis_source_races (
    analysis_run_id   INTEGER NOT NULL,
    target_horse_id   TEXT NOT NULL,
    source_race_id    TEXT NOT NULL,
    recency_rank      INTEGER NOT NULL,
    used              INTEGER NOT NULL DEFAULT 1,
    excluded_reason   TEXT,
    data_quality      REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (analysis_run_id, target_horse_id, source_race_id),
    UNIQUE (analysis_run_id, target_horse_id, recency_rank),
    FOREIGN KEY (analysis_run_id, target_horse_id)
        REFERENCES run_entries (analysis_run_id, horse_id),
    FOREIGN KEY (source_race_id, target_horse_id)
        REFERENCES results (race_id, horse_id),
    CHECK (recency_rank BETWEEN 1 AND 15),
    CHECK (used IN (0, 1)),
    CHECK (data_quality BETWEEN 0.0 AND 1.0),
    CHECK (
        (used = 1 AND excluded_reason IS NULL)
        OR (used = 0 AND length(trim(excluded_reason)) > 0)
    )
);

CREATE TABLE IF NOT EXISTS ability_definitions (
    ability_code   TEXT PRIMARY KEY,
    ability_name   TEXT NOT NULL UNIQUE,
    display_order  INTEGER NOT NULL UNIQUE,
    description    TEXT NOT NULL,
    CHECK (display_order BETWEEN 1 AND 8)
);

INSERT INTO ability_definitions (
    ability_code, ability_name, display_order, description
)
VALUES
    ('BASE_SPEED', '基礎スピード', 1, '巡航速度と追走力'),
    ('MAX_SPEED', '最高速度', 2, '終盤で到達できる絶対速度と今回の発揮速度'),
    ('STAMINA', 'スタミナ', 3, '距離と負荷に対する持続力'),
    ('POWER', 'パワー', 4, '重い馬場や負荷への対応力'),
    ('TIGHT_TURN', '小回り適性', 5, 'コーナーの多い条件への適応'),
    ('LONG_SPRINT', 'ロングスパート', 6, '長い加速区間を維持する力'),
    ('GEAR_CHANGE', 'ギアチェンジ', 7, '短区間で急加速する力'),
    ('DISTANCE_FIT', '距離適性', 8, '対象距離への適合度')
ON CONFLICT (ability_code) DO UPDATE SET
    ability_name = excluded.ability_name,
    display_order = excluded.display_order,
    description = excluded.description;

CREATE TABLE IF NOT EXISTS race_track_profiles (
    analysis_run_id        INTEGER NOT NULL,
    evaluated_race_id      TEXT NOT NULL,
    race_role              TEXT NOT NULL,
    surface_class          TEXT NOT NULL,
    deceleration_threshold REAL,
    confidence             REAL NOT NULL,
    evidence_count         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (analysis_run_id, evaluated_race_id),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id),
    FOREIGN KEY (evaluated_race_id) REFERENCES races (race_id),
    CHECK (race_role IN ('TARGET', 'SOURCE')),
    CHECK (surface_class IN ('FAST', 'STANDARD', 'SLOW', 'UNKNOWN')),
    CHECK (confidence BETWEEN 0.0 AND 1.0),
    CHECK (evidence_count >= 0)
);

CREATE TABLE IF NOT EXISTS past_run_ability_scores (
    analysis_run_id    INTEGER NOT NULL,
    horse_id           TEXT NOT NULL,
    source_race_id     TEXT NOT NULL,
    ability_code       TEXT NOT NULL,
    score              REAL,
    lower_score        REAL,
    upper_score        REAL,
    confidence         REAL NOT NULL DEFAULT 0.0,
    evaluation_status  TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, horse_id, source_race_id, ability_code),
    FOREIGN KEY (analysis_run_id, horse_id, source_race_id)
        REFERENCES analysis_source_races (
            analysis_run_id, target_horse_id, source_race_id
        ),
    FOREIGN KEY (ability_code) REFERENCES ability_definitions (ability_code),
    CHECK (score IS NULL OR score BETWEEN 0.0 AND 10.0),
    CHECK (lower_score IS NULL OR lower_score BETWEEN 0.0 AND 10.0),
    CHECK (upper_score IS NULL OR upper_score BETWEEN 0.0 AND 10.0),
    CHECK (confidence BETWEEN 0.0 AND 1.0),
    CHECK (evaluation_status IN ('MEASURED', 'ESTIMATED', 'NOT_TESTED')),
    CHECK (
        (evaluation_status = 'NOT_TESTED' AND score IS NULL)
        OR (evaluation_status <> 'NOT_TESTED' AND score IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS ability_evidence (
    evidence_id         INTEGER PRIMARY KEY,
    analysis_run_id     INTEGER NOT NULL,
    horse_id            TEXT NOT NULL,
    source_race_id      TEXT NOT NULL,
    ability_code        TEXT NOT NULL,
    evidence_type       TEXT NOT NULL,
    raw_value           REAL,
    adjusted_value      REAL,
    evidence_weight     REAL NOT NULL,
    direction           TEXT NOT NULL,
    reason_text         TEXT NOT NULL,
    display_priority    INTEGER NOT NULL DEFAULT 100,
    FOREIGN KEY (analysis_run_id, horse_id, source_race_id, ability_code)
        REFERENCES past_run_ability_scores (
            analysis_run_id, horse_id, source_race_id, ability_code
        ),
    CHECK (evidence_weight BETWEEN 0.0 AND 1.0),
    CHECK (direction IN ('POSITIVE', 'NEUTRAL', 'NEGATIVE'))
);

CREATE TABLE IF NOT EXISTS horse_ability_estimates (
    analysis_run_id    INTEGER NOT NULL,
    horse_id           TEXT NOT NULL,
    ability_code       TEXT NOT NULL,
    central_score      REAL,
    lower_score        REAL,
    upper_score        REAL,
    confidence         REAL NOT NULL DEFAULT 0.0,
    runs_used          INTEGER NOT NULL DEFAULT 0,
    stability_score    REAL,
    evaluation_status  TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, horse_id, ability_code),
    FOREIGN KEY (analysis_run_id, horse_id)
        REFERENCES run_entries (analysis_run_id, horse_id),
    FOREIGN KEY (ability_code) REFERENCES ability_definitions (ability_code),
    CHECK (central_score IS NULL OR central_score BETWEEN 0.0 AND 10.0),
    CHECK (lower_score IS NULL OR lower_score BETWEEN 0.0 AND 10.0),
    CHECK (upper_score IS NULL OR upper_score BETWEEN 0.0 AND 10.0),
    CHECK (confidence BETWEEN 0.0 AND 1.0),
    CHECK (runs_used BETWEEN 0 AND 5),
    CHECK (stability_score IS NULL OR stability_score BETWEEN 0.0 AND 1.0),
    CHECK (evaluation_status IN ('MEASURED', 'ESTIMATED', 'NOT_TESTED'))
);

-- Each ability owns its input and code fingerprint.  A recalculation can skip
-- an ability only when both fingerprints still match.
CREATE TABLE IF NOT EXISTS ability_input_fingerprints (
    analysis_run_id       INTEGER NOT NULL,
    horse_id              TEXT NOT NULL,
    ability_code          TEXT NOT NULL,
    input_fingerprint     TEXT NOT NULL,
    logic_fingerprint     TEXT NOT NULL,
    calculation_status    TEXT NOT NULL,
    calculated_at         TEXT,
    PRIMARY KEY (analysis_run_id, horse_id, ability_code),
    FOREIGN KEY (analysis_run_id, horse_id)
        REFERENCES run_entries (analysis_run_id, horse_id),
    FOREIGN KEY (ability_code) REFERENCES ability_definitions (ability_code),
    CHECK (calculation_status IN ('PENDING', 'CALCULATED', 'STALE', 'FAILED'))
);

-- The display ability remains the absolute peak.  Prediction code derives an
-- effective value from remaining energy without overwriting the peak.
CREATE TABLE IF NOT EXISTS max_speed_expression_profiles (
    analysis_run_id              INTEGER NOT NULL,
    horse_id                     TEXT NOT NULL,
    model_version                TEXT NOT NULL,
    absolute_max_speed_mps       REAL NOT NULL,
    absolute_max_speed_score     REAL NOT NULL,
    reference_remaining_energy   REAL NOT NULL,
    reserve_speed_slope          REAL NOT NULL,
    curve_points_json            TEXT NOT NULL,
    evidence_count               INTEGER NOT NULL,
    measurement_state            TEXT NOT NULL,
    input_fingerprint            TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, horse_id),
    FOREIGN KEY (analysis_run_id, horse_id)
        REFERENCES run_entries (analysis_run_id, horse_id),
    CHECK (absolute_max_speed_mps > 0.0),
    CHECK (absolute_max_speed_score BETWEEN 0.0 AND 10.0),
    CHECK (reference_remaining_energy BETWEEN 0.0 AND 1.0),
    CHECK (reserve_speed_slope >= 0.0),
    CHECK (evidence_count >= 0),
    CHECK (measurement_state IN ('MEASURED', 'ESTIMATED', 'NOT_TESTED'))
);

CREATE TABLE IF NOT EXISTS max_speed_expression_hypotheses (
    analysis_run_id     INTEGER NOT NULL,
    horse_id            TEXT NOT NULL,
    hypothesis_code     TEXT NOT NULL,
    probability         REAL NOT NULL,
    reserve_speed_slope REAL NOT NULL,
    PRIMARY KEY (analysis_run_id, horse_id, hypothesis_code),
    FOREIGN KEY (analysis_run_id, horse_id)
        REFERENCES max_speed_expression_profiles (analysis_run_id, horse_id),
    CHECK (hypothesis_code IN ('LOW', 'CENTER', 'HIGH')),
    CHECK (probability BETWEEN 0.0 AND 1.0),
    CHECK (reserve_speed_slope >= 0.0)
);

CREATE TABLE IF NOT EXISTS prediction_cache_revisions (
    analysis_run_id          INTEGER PRIMARY KEY,
    data_revision            TEXT NOT NULL,
    ability_revision         TEXT NOT NULL,
    prediction_logic_hash    TEXT NOT NULL,
    cached_result_hash       TEXT,
    updated_at               TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id)
);

CREATE INDEX IF NOT EXISTS idx_source_races_source
    ON analysis_source_races (source_race_id);

CREATE INDEX IF NOT EXISTS idx_scores_ability
    ON past_run_ability_scores (ability_code, evaluation_status);

CREATE INDEX IF NOT EXISTS idx_estimates_run
    ON horse_ability_estimates (analysis_run_id, ability_code, central_score DESC);

CREATE INDEX IF NOT EXISTS idx_ability_fingerprints_status
    ON ability_input_fingerprints (analysis_run_id, calculation_status);

COMMIT;
