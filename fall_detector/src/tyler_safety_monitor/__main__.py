"""Explicit launch of the observation-only dashboard."""

from __future__ import annotations

import argparse
import math
import multiprocessing
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibration/replay observation dashboard; no emergency alerts")
    launch = parser.add_mutually_exclusive_group()
    launch.add_argument("--show", action="store_true", help="open the dashboard immediately (development default)")
    launch.add_argument("--start-minimized", action="store_true", help="explicitly start in the tray; development opens the dashboard by default")
    parser.add_argument("--model", type=Path, help="local pose model; never downloaded at startup")
    parser.add_argument("--no-camera", action="store_true", help="open controls without accessing camera")
    parser.add_argument("--quit-after", type=float, help="bounded smoke-test runtime in seconds")
    parser.add_argument("--diagnostics", action="store_true", help="save startup path/file checks only; no imagery or features")
    args = parser.parse_args()
    if args.quit_after is not None and (not math.isfinite(args.quit_after) or not 0 < args.quit_after <= 86400):
        parser.error("--quit-after must be finite and between zero and 86400 seconds")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .dashboard import Dashboard
    from .settings import data_directory

    application = QApplication(sys.argv[:1])
    application.setApplicationName("Tyler Safety Monitor")
    application.setQuitOnLastWindowClosed(False)
    model = args.model or data_directory() / "models" / "pose_landmarker_full.task"
    dashboard = Dashboard(model, enable_camera=not args.no_camera)
    if args.diagnostics:
        from .launch_diagnostics import write_startup_diagnostic
        try:
            report = write_startup_diagnostic(model, dashboard.pose_status.text())
            dashboard.pose_status.setAccessibleDescription(f"Startup diagnostic: {report}")
        except OSError as error:
            dashboard.pose_status.setAccessibleDescription(f"Startup diagnostic could not be saved: {error}")
    application.aboutToQuit.connect(dashboard.shutdown)
    # Development stays foreground until Tyler approves the final tray-first
    # default. The explicit option retains the intended production workflow.
    if not args.start_minimized or not dashboard.tray_available:
        dashboard.open_dashboard()
    if args.quit_after is not None:
        QTimer.singleShot(int(args.quit_after * 1000), application.quit)
    return application.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
