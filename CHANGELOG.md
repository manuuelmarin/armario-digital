# Changelog

## En desarrollo

- Añade importación por lotes, colecciones, etiquetas y filtros combinables.
- Añade tableros privados con imágenes locales, enlaces y collage con posiciones editables y arrastre.
- Añade consulta manual opcional de previsión meteorológica y caché local.
- Guarda huellas persistentes de las imágenes, verifica las copias y permite limpiar copias diarias tras confirmar y verificar las conservadas.
- Ajusta el límite del servidor para permitir el tamaño de petición anunciado.

- Selección de fotografía principal para el catálogo, los outfits y las maletas.
- Migración con copia previa para preservar los armarios existentes.

## Unreleased

- Add outfit detail, search, favorites filter and safe duplication.
- Duplicate trip lists, prepare a return list without moving garments, and print lists.

- Allow six photographs of up to 10 MiB each in the same request.
- Restrict image decoders before opening uploads and update Pillow.
- Validate backup images and verify the generated archive before reporting success.
- Restore a valid backup while preserving a damaged previous data directory.

## 0.2.0 — 2026-10-29

### Added

- First-run setup with user-defined spaces and no preloaded inventory.
- An isolated, temporary demo with original garment illustrations.
- Responsive images, a 1,024 px preview and a master up to 4,096 px, plus a photo viewer.
- Inventory sorting, filter-preserving location tabs and searchable garment selectors.
- A local typography system, design tokens and responsive layouts across the product.
- Product screenshots, contribution guidelines, security boundaries and a publication guide.

### Changed

- Replaced development-specific defaults and conversation-oriented documentation with reusable product configuration and guides.
- Preserved existing inventory records during schema upgrades; extended backup compatibility to image previews.
- Reduced outfit-list database queries and kept bulk actions contextual to a selection.
- Collapsed advanced filters on small screens and improved form labels and keyboard focus.

## 0.1.0 — 2026-10-29

Initial preview: inventory, local photographs, locations, outfits, packing lists, SQLite migrations and recoverable backups.
