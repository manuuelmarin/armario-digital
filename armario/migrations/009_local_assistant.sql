CREATE TABLE ai_settings (
 id INTEGER PRIMARY KEY CHECK(id=1),
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
 paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0,1))
);
INSERT INTO ai_settings(id) VALUES (1);
CREATE TABLE garment_profiles (
 garment_id INTEGER PRIMARY KEY REFERENCES garments(id) ON DELETE CASCADE,
 revision INTEGER NOT NULL CHECK(revision>0),
 profile_json TEXT NOT NULL,
 source_name TEXT NOT NULL DEFAULT '',
 source_hash TEXT NOT NULL DEFAULT '',
 provenance_json TEXT NOT NULL,
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE ai_jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 kind TEXT NOT NULL CHECK(kind IN ('check','vision','outfit')),
 garment_id INTEGER REFERENCES garments(id) ON DELETE SET NULL,
 status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','completed','failed','cancelled','stale')),
 input_json TEXT NOT NULL,
 result_json TEXT,
 model TEXT NOT NULL DEFAULT '',
 model_digest TEXT NOT NULL DEFAULT '',
 prompt_version TEXT NOT NULL,
 error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 started_at TEXT,
 finished_at TEXT
);
CREATE INDEX ai_jobs_queue ON ai_jobs(status,id);
CREATE INDEX ai_jobs_garment ON ai_jobs(garment_id,id);
CREATE TABLE outfit_origins (
 outfit_id INTEGER PRIMARY KEY REFERENCES outfits(id) ON DELETE CASCADE,
 provenance_json TEXT NOT NULL
);
