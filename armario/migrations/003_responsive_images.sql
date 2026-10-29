-- Optional derivatives keep existing photographs and older backups compatible.
ALTER TABLE garment_images ADD COLUMN preview TEXT;
ALTER TABLE garment_images ADD COLUMN width INTEGER CHECK(width > 0);
ALTER TABLE garment_images ADD COLUMN height INTEGER CHECK(height > 0);
ALTER TABLE garment_images ADD COLUMN preview_width INTEGER CHECK(preview_width > 0);
ALTER TABLE garment_images ADD COLUMN thumbnail_width INTEGER CHECK(thumbnail_width > 0);
CREATE UNIQUE INDEX garment_images_preview ON garment_images(preview) WHERE preview IS NOT NULL;
CREATE INDEX outfit_items_garment ON outfit_items(garment_id);
CREATE INDEX trip_items_garment ON trip_items(garment_id);
