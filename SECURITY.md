# Security

## Supported use

The supported deployment is one local process launched through `run.py`, listening on `127.0.0.1`. The operating-system lock excludes a second server or an offline restore using the same data directory. Multiple WSGI processes and shared network folders are not supported.

Requests use host validation and CSRF protection. Uploads are validated by decoded image content, not their extension. Images are re-encoded without EXIF metadata. The server does not fetch user-provided URLs. Inventories, images, session keys and backups are excluded from source control.

## Reporting a vulnerability

Use GitHub private vulnerability reporting if it is enabled for the repository. Otherwise arrange a private channel with the maintainers before sharing exploit details or affected data. Public reports should not contain photographs, inventories, secrets or private filesystem paths.

Include the application version, operating system, reproduction steps using fictional data, the affected behavior and expected impact.

## Before network hosting

Internet or shared-network hosting needs a separate review of authentication, authorization, TLS, process-level concurrency, upload limits and operational recovery. The local preview does not claim those capabilities.
