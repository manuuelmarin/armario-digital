-- Hashes represent the accepted local files, independently of backup manifests.
CREATE TABLE image_integrity (
 name TEXT PRIMARY KEY,
 sha256 TEXT NOT NULL CHECK(length(sha256)=64)
);
