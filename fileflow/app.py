from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from .storage import SettingsStore
from .ui import MainWindow, configure_fonts
from .diagnostics import event, configure as configure_diagnostics


def main():
    parser = argparse.ArgumentParser(description="FileFlow local desktop organizer")
    parser.add_argument("--data-dir", type=Path, help="Use a separate local settings folder")
    parser.add_argument("--smoke-test", type=Path, help="Run isolated package checks and write a JSON report, then exit")
    parser.add_argument('--diagnostics', type=Path, help='Opt-in structured JSONL log; parent must exist')
    parser.add_argument('--memory-test', type=Path, help='Run isolated memory benchmark and write report')
    parser.add_argument('--memory-minutes', type=float, default=0, help='Sustained duration for isolated memory diagnostics')
    parser.add_argument('--lifecycle-test', type=Path, help='Isolated lifecycle diagnostic report (requires --data-dir)')
    parser.add_argument('--lifecycle-scenario', choices=('tray', 'close', 'background', 'monitoring', 'pending', 'active', 'hold', 'startup-failure'), default='tray')
    args = parser.parse_args()
    if args.lifecycle_test and not args.data_dir:
        parser.error('--lifecycle-test requires an isolated --data-dir')
    configure_diagnostics(args.diagnostics)
    event('application_start')
    if args.memory_test:
        from tools.profile_memory import main as memory_main
        memory_main(args.memory_test, args.memory_minutes)
        return 0
    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FileFlow.Desktop.1")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("FileFlow")
    app.setOrganizationName("FileFlow")
    app.setQuitOnLastWindowClosed(False)
    configure_fonts(app)
    if args.smoke_test:
        return smoke_test(app, args.smoke_test)
    store = SettingsStore(args.data_dir / "settings.json" if args.data_dir else None)
    # A Windows named mutex prevents duplicate instances without creating any files.
    import hashlib
    digest = hashlib.sha256(str(store.path.absolute()).casefold().encode()).hexdigest()[:20]
    mutex = None
    if os.name == "nt":
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        mutex = kernel.CreateMutexW(None, False, f"Local\\FileFlow-{digest}")
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            kernel.CloseHandle(mutex)
            event('mutex_duplicate')
            if args.lifecycle_test:
                args.lifecycle_test.write_text(json.dumps({'duplicate': True}), encoding='utf-8')
                return 17
            QMessageBox.information(None, "FileFlow", "FileFlow يعمل بالفعل. / FileFlow is already running.")
            return 0
        event('mutex_acquired')
    window = None
    try:
        if args.lifecycle_test and args.lifecycle_scenario == 'startup-failure':
            event('diagnostic_startup_failure')
            args.lifecycle_test.write_text(json.dumps({'startup_failure': True}), encoding='utf-8')
            return 19
        window = MainWindow(store)
        window.shutdown_finished.connect(app.quit)
        window.show()
        if args.lifecycle_test:
            from .probes import LifecycleProbe
            probe = LifecycleProbe(window, args.lifecycle_scenario, args.lifecycle_test)
        app.aboutToQuit.connect(lambda: event('qt_about_to_quit'))
        result = app.exec()
        if args.lifecycle_test: probe.finish(result)
        return result
    finally:
        clean = True
        if window:
            try: window.service.shutdown()
            except TimeoutError:
                clean = False
                # Retain ownership until process exit if a driver is stuck. Never
                # release singleton protection while an active worker could move files.
                globals().setdefault('_retained_mutexes', []).append(mutex)
                event('application_cleanup_pending')
        if mutex and clean:
            kernel.CloseHandle(mutex)
            event('mutex_released')
        event('application_exit', clean=clean)


def smoke_test(app, report_path):
    """Explicit diagnostics touch only a new TemporaryDirectory and the requested report."""
    from .engine import Organizer
    from .models import Folder, Settings
    report = {"ok": False}
    try:
        with tempfile.TemporaryDirectory(prefix="FileFlow-smoke-") as temp:
            root = Path(temp) / "Inbox"
            root.mkdir()
            (root / "proof.txt").write_text("FileFlow", encoding="utf-8")
            folder = Folder(str(root), confirmed=True)
            results = Organizer(interval=.01, quiet=.03).organize(folder)
            assert results[0].status == "success", results
            assert (root / "Documents" / "proof.txt").read_text() == "FileFlow"
            store = SettingsStore(Path(temp) / "settings.json")
            store.save(Settings(folders=[folder]))
            window = MainWindow(store)
            try:
                app.processEvents()
                assert window.layoutDirection().name == "RightToLeft"
                window.service.configure([folder], True)
                deadline = time.monotonic() + 10
                while not window._watching and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                assert window._watching == 1, "watchdog did not start"
                (root / "watched.txt").write_bytes(b"watchdog packaged check")
                deadline = time.monotonic() + 10
                while not (root / "Documents/watched.txt").exists() and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                assert (root / "Documents/watched.txt").exists(), "watchdog did not move the file"
                window.service.configure([folder], False)
                deadline = time.monotonic() + 5
                while window._watching and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                assert window._watching == 0, "watchdog did not stop"
                window.settings.theme = "dark"
                window.build()
                app.processEvents()
                window.change_language()
                assert window.layoutDirection().name == "LeftToRight"
                window.render_history()
                window.navigate('history', animate=False)
                assert window.stack.currentWidget() is window.pages['history']
                assert window.history_table.rowCount() >= 1
                window.history_table.setCurrentCell(0, 0)
                assert window.open_button.isEnabled()
            finally:
                window.quit_app()
                deadline = time.monotonic() + 5
                while not window._closed and time.monotonic() < deadline:
                    app.processEvents(); time.sleep(.01)
                assert window._closed, 'shutdown did not complete'
            report = {"ok": True, "move": True, "settings": True, "arabic_rtl": True,
                      "english_ltr": True, "watchdog": True, "monitoring_stop": True,
                      "dark_mode": True, "shutdown": True, "isolated": True}
            report.update(history_navigation=True, history_details=True)
    except Exception as error:
        report["error"] = repr(error)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
