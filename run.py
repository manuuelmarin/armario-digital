"""Single entry point for Windows/Linux; local serving and offline recovery."""

import argparse
import threading
import webbrowser
from datetime import UTC, datetime
from pathlib import Path

from armario import create_app, default_data_dir
from armario.backups import create_backup, process_lock, restore_backup, verify_backup


def main():
    parser = argparse.ArgumentParser(description="Armario Digital — aplicación local")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--dev", action="store_true", help="Recargar código sin depurador remoto")
    parser.add_argument("--no-browser", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("backup")
    verify = sub.add_parser("verify")
    verify.add_argument("archive", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    root = args.data_dir.expanduser().resolve()
    if args.command == "verify":
        print(verify_backup(args.archive))
        return
    if args.command == "restore":
        print("Contenido verificado:", verify_backup(args.archive))
        if not args.confirm:
            print("No se ha modificado nada. Cierra la app y repite con --confirm para restaurar.")
            return
        with process_lock(root):
            result, old = restore_backup(args.archive, root)
        print("Restauración completada:", result)
        if old:
            print("Datos anteriores conservados en:", old)
        return

    def serve():
        with process_lock(root):
            app = create_app({"DATA_DIR": root})
            if args.command == "backup":
                print(create_backup(root))
                return
            day = datetime.now(UTC).strftime("%Y%m%d")
            if not list((root / "backups").glob(f"daily-{day}*.zip")):
                create_backup(root, prefix="daily")
            if not args.no_browser:
                opener = threading.Timer(1, lambda: webbrowser.open("http://127.0.0.1:8765"))
                opener.daemon = True
                opener.start()
            print("Armario Digital: http://127.0.0.1:8765 — Ctrl+C para cerrar", flush=True)
            if args.dev:
                from werkzeug.serving import run_simple

                run_simple("127.0.0.1", 8765, app, use_debugger=False, threaded=True)
            else:
                from waitress import serve as waitress_serve

                waitress_serve(
                    app, host="127.0.0.1", port=8765, threads=4, max_request_body_size=32 * 1024**2
                )

    if args.dev and args.command is None:
        from werkzeug._reloader import run_with_reloader

        extras = [
            str(path)
            for path in Path("armario").rglob("*")
            if path.suffix in {".html", ".css", ".js"}
        ]
        run_with_reloader(serve, extra_files=extras, reloader_type="stat")
    else:
        serve()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        raise SystemExit(f"No se ha completado la operación: {error}") from error
