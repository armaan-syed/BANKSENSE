CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    intent TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    model TEXT NOT NULL,
    priority TEXT NOT NULL,
    priority_reason TEXT NOT NULL,
    summary TEXT,
    summary_status TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'submitted' CHECK (source IN ('submitted', 'demo')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON complaints (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_intent ON complaints (intent);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints (priority);
