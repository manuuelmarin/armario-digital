import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

import run


def test_reopen_uses_active_port(tmp_path, monkeypatch):
    root = tmp_path / "wardrobe"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "run.py", "--data-dir", str(root), "--port", str(port), "--no-browser"]
    )
    try:
        for _ in range(100):
            if (root / "instance.info").exists():
                break
            assert proc.poll() is None
            time.sleep(0.1)
        assert (root / "instance.info").is_file()
        opened = []
        monkeypatch.setattr(run.webbrowser, "open", opened.append)
        monkeypatch.setattr(sys, "argv", ["run.py", "--data-dir", str(root), "--reopen"])
        run.main()
        assert opened == [f"http://127.0.0.1:{port}"]
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows Shell")
def test_windows_shortcut(tmp_path):
    script = Path("escritorio.ps1").resolve()
    icon = Path("armario/static/armario.ico").resolve()
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-File",
            str(script),
            "-IconPath",
            str(icon),
            "-DesktopPath",
            str(tmp_path),
        ],
        check=True,
    )
    shortcut = tmp_path / "Mi Armario Digital.lnk"
    assert shortcut.is_file()
    result = subprocess.check_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ARMARIO_LINK); "
            "$s.Arguments; $s.IconLocation; $s.WorkingDirectory",
        ],
        env={**os.environ, "ARMARIO_LINK": str(shortcut)},
        text=True,
    )
    assert "--reopen" in result
    assert str(icon).lower() in result.lower()
    assert str(script.parent).lower() in result.lower()
