CREATE TABLE locations (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(name) BETWEEN 1 AND 80)
);
CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE);
INSERT INTO categories(name) VALUES ('Camisetas'),('Camisas'),('Punto'),('Sudaderas'),('Pantalones'),('Chaquetas'),('Abrigos'),('Calzado'),('Deporte'),('Accesorios'),('Otros');
CREATE TABLE garments (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
 category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
 location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
 brand TEXT NOT NULL DEFAULT '', size TEXT NOT NULL DEFAULT '', color TEXT NOT NULL DEFAULT '',
 notes TEXT NOT NULL DEFAULT '', price_cents INTEGER CHECK(price_cents >= 0),
 purchased_on TEXT, favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)),
 archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX garments_location ON garments(location_id, archived);
CREATE INDEX garments_category ON garments(category_id, archived);
CREATE TABLE garment_seasons (
 garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
 season TEXT NOT NULL CHECK(season IN ('Primavera','Verano','Otoño','Invierno')),
 PRIMARY KEY(garment_id,season)
);
CREATE TABLE garment_images (
 id INTEGER PRIMARY KEY, garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
 filename TEXT NOT NULL UNIQUE, thumbnail TEXT NOT NULL UNIQUE, digest TEXT NOT NULL,
 UNIQUE(garment_id,digest)
);
CREATE TABLE garment_movements (
 id INTEGER PRIMARY KEY, garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
 from_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
 to_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
 reason TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 CHECK(from_id != to_id)
);
CREATE TABLE outfits (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
 notes TEXT NOT NULL DEFAULT '', occasion TEXT NOT NULL DEFAULT '',
 favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1))
);
CREATE TABLE outfit_items (
 outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
 garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE RESTRICT,
 PRIMARY KEY(outfit_id,garment_id)
);
