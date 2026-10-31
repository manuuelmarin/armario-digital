# Security

## Supported use

The supported deployment is one local process launched through `run.py`, listening on `127.0.0.1`. The operating-system lock excludes a second server or an offline restore using the same data directory. Multiple WSGI processes and shared network folders are not supported.

Requests use host validation and CSRF protection. Uploads are validated by decoded image content, not their extension. Images are re-encoded without EXIF metadata. The server does not fetch user-provided URLs. Inventories, images, session keys and backups are excluded from source control.

## Reporting a vulnerability

Use GitHub private vulnerability reporting if it is enabled for the repository. Otherwise arrange a private channel with the maintainers before sharing exploit details or affected data. Public reports should not contain photographs, inventories, secrets or private filesystem paths.

Include the application version, operating system, reproduction steps using fictional data, the affected behavior and expected impact.

## Before network hosting

Internet or shared-network hosting needs a separate review of authentication, authorization, TLS, process-level concurrency, upload limits and operational recovery. The local preview does not claim those capabilities.

## Optional local models

AI assistance is disabled by default. Users prepare Ollama and explicitly request analysis or generation. The adapter only connects to `127.0.0.1:11434`, ignores environment proxies, rejects redirects and never downloads models or falls back to cloud. Only two explicit local model tags are admitted. Configure Ollama itself with `OLLAMA_NO_CLOUD=1` and a loopback bind; the application does not reconfigure another process.

Vision receives a resized main photograph after its SHA-256 check. Text receives approved descriptions and candidate IDs, without photos, personal notes, purchase data or location names. Model output and user descriptions are untrusted data: bounded JSON/schema validation, escaped HTML, real-ID/constraint checks and source/revision revalidation precede use. No model receives executable application tools. Human approval is required to replace a reviewed description or save an outfit.

The original brand, size, purchase, notes and location fields are not appended to text requests. Free text in approved profiles is transmitted to the local service as written, so it can contain information users explicitly enter there. Source checks include actual file bytes, not just stored hashes. Unique approval IDs prevent a reused SQLite garment ID from validating an older recommendation. Startup and recovery also validate required schema tables/columns against the migrations, including the required settings row.

The queue does not hold a mutation lock or database transaction during inference. Cancellation discards late responses but may not stop an already running Ollama inference. A timeout pauses subsequent inference. Profiles, task snapshots and generation provenance are private local data included in unencrypted backups. Clearing the active task history does not erase prior backups. Model weights, Ollama configuration and its own logs are managed separately. See [local AI](docs/LOCAL_AI.md) for setup and verification limits.
