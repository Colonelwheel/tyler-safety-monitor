"""Exercise the Windows desktop launcher without importing the live monitor."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows desktop launcher")
def test_desktop_launcher_passes_local_model_and_disables_bytecode_writes(tmp_path):
    detector = Path(__file__).resolve().parents[2]
    launcher = detector / "Start Monitor.cmd"
    pythonw = detector / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.is_file():
        pytest.skip("Desktop launcher requires its existing isolated environment")

    # A fresh package on PYTHONPATH captures startup arguments and cannot open
    # a camera, load Qt, or read the real application's saved data.
    modules = tmp_path / "fake modules with spaces"
    package = modules / "tyler_safety_monitor"
    package.mkdir(parents=True)
    with (package / "__init__.py").open("x", encoding="utf-8") as stream:
        stream.write("")
    with (package / "__main__.py").open("x", encoding="utf-8") as stream:
        stream.write(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "payload = {'args': sys.argv[1:], "
            "'local_app_data': os.environ['LOCALAPPDATA'], "
            "'dont_write_bytecode': sys.dont_write_bytecode}\n"
            "with Path(os.environ['TSM_LAUNCH_TEST_MARKER']).open('x', encoding='utf-8') as output:\n"
            "    json.dump(payload, output)\n"
        )
    local_app_data = tmp_path / "Local app data with spaces"
    model = local_app_data / "TylerSafetyMonitor" / "models" / "pose_landmarker_full.task"
    model.parent.mkdir(parents=True)
    with model.open("xb") as stream:
        stream.write(b"synthetic model sentinel; never loaded")
    marker = tmp_path / "launch-result.json"
    environment = os.environ.copy()
    environment.update(
        LOCALAPPDATA=str(local_app_data),
        PYTHONPATH=str(modules),
        TSM_LAUNCH_TEST_MARKER=str(marker),
    )
    # Remove an inherited -B equivalent so the checked-in launcher's -B flag
    # itself must prevent writing cached modules.
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
        [environment.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)],
        cwd=tmp_path,
        env=environment,
        shell=False,
        capture_output=True,
        text=True,
        timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert completed.returncode == 0, completed.stderr
    deadline = time.monotonic() + 5
    payload = None
    while time.monotonic() < deadline:
        if marker.is_file():
            try:
                payload = json.loads(marker.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # The exclusive marker can become visible before flush.
            else:
                break
        time.sleep(0.02)
    assert payload is not None, "Fake desktop application did not report startup within five seconds"
    assert payload["args"] == ["--model", str(model)]
    assert payload["local_app_data"] == str(local_app_data)
    assert payload["dont_write_bytecode"] is True
    assert not (package / "__pycache__").exists()
    assert model.read_bytes() == b"synthetic model sentinel; never loaded"
