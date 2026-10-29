-- Existing photographs keep their original order until a cover is selected.
ALTER TABLE garment_images ADD COLUMN is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0, 1));
CREATE UNIQUE INDEX garment_images_one_primary ON garment_images(garment_id) WHERE is_primary = 1;
