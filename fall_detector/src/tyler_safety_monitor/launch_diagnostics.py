"""Opt-in startup path diagnostics; no imagery, features or settings contents."""

from datetime import datetime, timezone
import ctypes
import json
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

from .settings import data_directory


def probe_path(path: Path) -> dict:
    result = {"path": str(path)}
    try:
        info = path.stat()
        result.update(is_file=stat.S_ISREG(info.st_mode), size=info.st_size)
        if result["is_file"]:
            with path.open("rb") as stream:
                stream.read(1)  # Check readability without retaining file contents.
            result["readable"] = True
    except OSError as error:
        result.update(error=type(error).__name__, errno=error.errno,
                      winerror=getattr(error, "winerror", None), detail=str(error))
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        attributes = kernel.GetFileAttributesW
        attributes.argtypes = [ctypes.c_wchar_p]
        attributes.restype = ctypes.c_uint32
        ctypes.set_last_error(0)
        value = attributes(str(path))
        result["windows_attributes"] = value
        result["windows_error"] = ctypes.get_last_error() if value == 0xffffffff else 0
        create = kernel.CreateFileW
        create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                           ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create.restype = ctypes.c_void_p
        handle = create(str(path), 0, 7, None, 3, 0x02000000, None)
        if handle != ctypes.c_void_p(-1).value:
            close = kernel.CloseHandle
            close.argtypes = [ctypes.c_void_p]
            try:
                final = kernel.GetFinalPathNameByHandleW
                final.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
                final.restype = ctypes.c_uint32
                name = ctypes.create_unicode_buffer(32768)
                if final(handle, name, len(name), 0):
                    result["final_path"] = name.value
                identify = kernel.GetFileInformationByHandleEx
                identify.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
                identity = ctypes.create_string_buffer(24)
                if identify(handle, 18, identity, 24):
                    result["file_identity"] = identity.raw.hex()
            finally:
                close(handle)
    return result


def startup_snapshot(model: Path, status: str) -> dict:
    runtime = data_directory()
    report = {"schema_version": 1, "pid": os.getpid(), "parent_pid": os.getppid(),
              "executable": sys.executable, "prefix": sys.prefix, "cwd": os.getcwd(),
              "local_app_data": os.environ.get("LOCALAPPDATA"), "runtime": str(runtime),
              "model": probe_path(model), "model_parent": probe_path(model.parent),
              "runtime_parent": probe_path(runtime.parent), "runtime_directory": probe_path(runtime),
              "settings_directory": probe_path(runtime / "config"), "pose_status": status,
              "modules": {name: getattr(sys.modules.get(name), "__file__", None)
                          for name in ("__main__", "tyler_safety_monitor.__main__",
                                       "tyler_safety_monitor.dashboard",
                                       "tyler_safety_monitor.settings")}}
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        getenv = kernel.GetEnvironmentVariableW
        getenv.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        getenv.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        if getenv("LOCALAPPDATA", buffer, len(buffer)):
            report["native_local_app_data"] = buffer.value
    return report


def write_startup_diagnostic(model: Path, status: str) -> Path:
    report = startup_snapshot(model, status)
    directory = data_directory() / "diagnostics"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"startup-{stamp}-{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return path
