CREATE TABLE trips (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
 origin_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
 destination_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
 starts_on TEXT, ends_on TEXT, notes TEXT NOT NULL DEFAULT '',
 CHECK(origin_id != destination_id), CHECK(ends_on IS NULL OR starts_on IS NULL OR ends_on >= starts_on)
);
CREATE TABLE trip_items (
 id INTEGER PRIMARY KEY, trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
 garment_id INTEGER REFERENCES garments(id) ON DELETE RESTRICT, label TEXT,
 packed INTEGER NOT NULL DEFAULT 0 CHECK(packed IN (0,1)),
 CHECK((garment_id IS NOT NULL AND label IS NULL) OR (garment_id IS NULL AND length(label) BETWEEN 1 AND 120)),
 UNIQUE(trip_id,garment_id), UNIQUE(trip_id,label)
);
