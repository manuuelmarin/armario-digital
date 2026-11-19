# Repository guidelines

## Product boundaries

Armario Digital is a local-first, single-user wardrobe application. The interface is Spanish. The daily Windows client is a static site served by GitHub Pages. It stores SQLite and images in a user-selected directory. The historical Python application remains a compatibility and recovery reference.

## Data integrity

- Never commit inventories, personal photographs, session keys, backups or environment files.
- A clean installation has no locations or garments. Example data belongs in isolated demo and test fixtures.
- Packing lists never move garments implicitly. Transfers are explicit transactions that preserve garment identity.
- Schema changes require a recoverable snapshot and a populated-database migration test. Preserve existing locations and relationships during upgrades.
- Keep compatibility with supported backup versions. Do not discard image derivatives referenced by a backup.

## Implementation

- Keep request handling, validation, SQLite access, image processing and recovery separated by responsibility.
- Use parameterized SQL, named functions, explicit errors and type annotations where they clarify contracts.
- In the historical Python app, keep templates readable. Share controls and image markup through Jinja macros with their required context.
- Reuse design tokens, local fonts and SVG icons. Provide labels, keyboard access, focus styles and responsive layouts.
- In the historical Python app, support normal forms without JavaScript. Client-side code enhances selection, filtering and previews.
- Changes to packaging or distribution must document actual platform validation. Do not describe a preview as production-ready.

## Verification

Run the relevant tests, `python -m ruff check .` and `python -m ruff format --check .`.
For interface changes, run the real-browser workflow, inspect desktop and mobile, and check image loading and horizontal overflow. Use fictional fixtures exclusively.
Document changes to behavior, schema or supported recovery formats in the changelog and affected guides.
