"""Top-level only organizer. No copy/delete fallback and no silent replacement."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event, Lock
from typing import Callable
import ctypes
import os
import time

from .models import Folder, TEMP_EXTENSIONS, is_reparse, validate_root


@dataclass
class Activity:
    source: str
    destination: str = ""
    status: str = "success"
    detail: str = ""
    time: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)


def signature(path: Path):
    info = path.stat(follow_symlinks=False)
    return info.st_size, info.st_mtime_ns, info.st_ino


def wait_stable(path: Path, stop: Event, interval: float = 0.5, quiet: float = 2.0,
                timeout: float = 15.0, clock=time.monotonic, initial=None) -> bool:
    """Require multiple identical samples over a quiet window; cancellation is prompt."""
    start = unchanged = clock()
    previous = signature(path)
    if initial and initial[0] == previous:
        unchanged = initial[1]
    while clock() - start < timeout:
        if stop.is_set():
            return False
        if clock() - unchanged >= quiet:
            return True
        if stop.wait(interval):
            return False
        current = signature(path)
        if current != previous:
            unchanged = clock()
            previous = current
        elif clock() - unchanged >= quiet:
            return True
    return False


@contextmanager
def protected_source(path: Path):
    """On Windows, deny writers and deleters for the entire final rename operation."""
    if os.name != "nt":
        yield None
        return
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    # GENERIC_READ | DELETE, share READ only, OPEN_EXISTING, OPEN_REPARSE_POINT.
    handle = kernel.CreateFileW(str(path), 0x80010000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield handle
    finally:
        kernel.CloseHandle(handle)


def rename_no_replace(source: Path, destination: Path, handle=None):
    if os.name == "nt" and handle is not None:
        from ctypes import wintypes
        class RenameInfo(ctypes.Structure):
            _fields_ = [("ReplaceIfExists", wintypes.BOOL), ("RootDirectory", wintypes.HANDLE),
                        ("FileNameLength", wintypes.DWORD), ("FileName", wintypes.WCHAR * (len(str(destination).encode("utf-16-le")) // 2 + 1))]
        info = RenameInfo()
        info.ReplaceIfExists = False
        info.FileNameLength = len(str(destination).encode("utf-16-le"))
        info.FileName = str(destination)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype = wintypes.BOOL
        if not kernel.SetFileInformationByHandle(handle, 3, ctypes.byref(info), ctypes.sizeof(info)):
            error = ctypes.get_last_error()
            if error in (80, 183):
                raise FileExistsError(str(destination))
            raise ctypes.WinError(error)
    elif os.name == "nt":
        os.rename(source, destination)  # Windows rename refuses replacement.
    else:
        # Tests/development on POSIX: link reserves destination atomically.
        os.link(source, destination, follow_symlinks=False)
        try:
            os.unlink(source)
        except OSError:
            # Both names remain; user data is preserved and the error is reported.
            raise


class Organizer:
    def __init__(self, callback: Callable[[Activity], None] = lambda _: None,
                 interval=0.5, quiet=2.0, timeout=15.0, excluded_directories=()):
        self.callback = callback
        self.interval, self.quiet, self.timeout = interval, quiet, timeout
        self._lock = Lock()
        self.excluded_directories = {Path(p).absolute() for p in excluded_directories}

    def organize(self, folder: Folder, stop: Event | None = None) -> list[Activity]:
        stop = stop or Event()
        if not folder.confirmed or stop.is_set():
            return []
        results = []

        def report(source, destination="", status="success", detail=""):
            activity = Activity(str(source), str(destination), status, detail,
                                datetime.now().astimezone().isoformat(timespec="seconds"))
            results.append(activity)
            self.callback(activity)

        with self._lock:
            try:
                folder.validate()
                root = validate_root(folder.path)
                if root in self.excluded_directories:
                    return []  # Never organize the application's own JSON/history directory.
                files = list(root.iterdir())
                reserved = {value.replace("\\", "/").split("/")[0].casefold()
                            for value in folder.destinations.values()}
                reserved.update(rule.destination.replace("\\", "/").split("/")[0].casefold()
                                for rule in folder.rules if rule.enabled)
                observations = {}
                for path in files:
                    try:
                        observations[path] = (signature(path), time.monotonic())
                    except OSError:
                        pass  # The per-file attempt below reports accessible failures.
            except (OSError, ValueError) as error:
                report(folder.path, status="error", detail=str(error))
                return results
            for source in files:
                if stop.is_set():
                    break
                try:
                    if (is_reparse(source) or not source.is_file() or source.suffix.lower() in TEMP_EXTENSIONS
                            or source.name.startswith(("~$", ".~"))):
                        continue
                    if source.name.casefold() in reserved:
                        raise ValueError("unsafe_destination")
                    if not wait_stable(source, stop, self.interval, self.quiet, self.timeout,
                                       initial=observations.get(source)):
                        if not stop.is_set():
                            report(source, status="deferred", detail="unstable")
                        continue
                    before = signature(source)
                    moved_destination = None
                    with protected_source(source) as handle:
                        if stop.is_set():
                            break
                        if signature(source) != before or is_reparse(source):
                            report(source, status="deferred", detail="unstable")
                            continue
                        validate_root(root)
                        target = root
                        # Validate every destination component before creating it.
                        for part in folder.destination_for(source).split("/"):
                            target = target / part
                            if target.exists() or target.is_symlink():
                                if is_reparse(target) or not target.is_dir():
                                    raise ValueError("unsafe_destination")
                            else:
                                target.mkdir()
                        destination = target / source.name
                        number = 0
                        while True:
                            if stop.is_set():
                                break
                            try:
                                rename_no_replace(source, destination, handle)
                                moved_destination = destination
                                break
                            except FileExistsError:
                                number += 1
                                destination = target / f"{source.stem} ({number}){source.suffix}"
                    if moved_destination:
                        report(source, moved_destination)
                except FileNotFoundError:
                    # A file may legitimately disappear between enumeration and inspection.
                    continue
                except (OSError, ValueError) as error:
                    report(source, status="error", detail=str(error))
        return results
