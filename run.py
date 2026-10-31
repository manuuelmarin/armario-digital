"""Single entry point for Windows/Linux; local serving and offline recovery."""

import argparse
import sqlite3
import tempfile
import threading
import webbrowser
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from armario import create_app, default_data_dir
from armario.backups import create_backup, process_lock, restore_backup, verify_backup


def main():
    parser = argparse.ArgumentParser(description="Armario Digital — aplicación local")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--dev", action="store_true", help="Recargar código sin depurador remoto")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--demo", action="store_true", help="Inventario ficticio en una carpeta temporal aislada"
    )
    parser.add_argument("--port", type=int, default=8765)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("backup")
    verify = sub.add_parser("verify")
    verify.add_argument("archive", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    if args.demo and (args.command or args.dev):
        parser.error("El modo demo no se combina con comandos de recuperación o --dev.")
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
            app = create_app({"DATA_DIR": root, "DEMO_MODE": args.demo, "DEV_MODE": args.dev})
            if args.demo:
                from armario.demo import seed_demo

                seed_demo(root)
            if args.command == "backup":
                print(create_backup(root))
                return
            day = datetime.now(UTC).strftime("%Y%m%d")
            if not list((root / "backups").glob(f"daily-{day}*.zip")):
                create_backup(root, prefix="daily")
            if not args.no_browser:
                opener = threading.Timer(
                    1, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")
                )
                opener.daemon = True
                opener.start()
            print(f"Armario Digital: http://127.0.0.1:{args.port} — Ctrl+C para cerrar", flush=True)
            from armario.ai_jobs import AIWorker

            worker = AIWorker(root, app.config["MUTATION_LOCK"])
            app.extensions["ai_worker"] = worker
            worker.start()
            try:
                if args.dev:
                    from werkzeug.serving import run_simple

                    run_simple("127.0.0.1", args.port, app, use_debugger=False, threaded=True)
                else:
                    from waitress import serve as waitress_serve

                    waitress_serve(
                        app,
                        host="127.0.0.1",
                        port=args.port,
                        threads=4,
                        max_request_body_size=64 * 1024**2,
                    )
            finally:
                worker.stop()

    if args.demo:
        with tempfile.TemporaryDirectory(prefix="armario-demo-") as temporary:
            root = Path(temporary)
            serve()
    elif args.dev and args.command is None:
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
    except (RuntimeError, ValueError, OSError, sqlite3.Error, zipfile.BadZipFile) as error:
        raise SystemExit(f"No se ha completado la operación: {error}") from error
