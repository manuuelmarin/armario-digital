ALTER TABLE garment_images ADD COLUMN sort_order INTEGER;
UPDATE garment_images SET sort_order = id;
