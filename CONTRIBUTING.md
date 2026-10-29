# Contributing

Contributions should improve the wardrobe workflow while keeping installation and maintenance straightforward.

## Set up

Use Python 3.12 and an isolated virtual environment. Install `requirements-dev.txt` and run `python run.py --dev`. The application uses the same entry point on every platform. Windows launchers are convenience wrappers.

Use `python run.py --demo` to explore the product with fictional data. The demo uses temporary storage and is separate from a normal inventory.

## Propose a change

Create a branch from `main` and keep the change focused. Describe the problem, the resulting behavior, how it was verified and any data or compatibility implications. Include screenshots for interface changes, generated with the demo or synthetic fixtures.

Existing inventory or backup data must survive an update. For schema changes, add a versioned migration and test it with populated relationships. Update the model and recovery documentation when formats change.

## Validate

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m djlint armario/templates --check
```

For browser tests, install Chromium with `python -m playwright install chromium` and enable `RUN_BROWSER_TESTS=1`. See [TESTING.md](docs/TESTING.md) for platform-specific commands.

Do not include real photographs, database files, account information, absolute user paths or conversation transcripts in issues, examples or screenshots. Fonts and other third-party assets need their license notices.

Licensing for public code distribution has not yet been selected. Contributions should remain within the repository's current access and distribution policy until that decision is recorded.
