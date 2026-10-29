"""Reproduce 1.2's hidden-window Quit using its real entry point, tray action and mutex.
The diagnostic rescue is cooperative QApplication.quit, never a process kill.
"""
from pathlib import Path
import json
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from fileflow import app as entry
from fileflow.models import Folder, Settings
from fileflow.storage import SettingsStore

report_path = Path(sys.argv[1]).absolute()
report = {'events': [], 'rescue_required': False}
started = time.perf_counter()
def record(event, **fields):
    report['events'].append({'event': event, 'seconds': time.perf_counter() - started, **fields})
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
with tempfile.TemporaryDirectory(prefix='FileFlow-baseline-') as temporary:
    root = Path(temporary); inbox = root / 'Inbox'; inbox.mkdir()
    store = SettingsStore(root / 'Config/settings.json')
    store.save(Settings(folders=[Folder(str(inbox), True)], tray=True))
    original = entry.MainWindow
    def create(store):
        window = original(store)
        record('startup', tray_available=QSystemTrayIcon.isSystemTrayAvailable())
        def close_to_tray():
            window.close(); record('window_close', visible=window.isVisible(), closed=window._closed)
        def quit_action():
            record('quit_action')
            window.tray_icon.contextMenu().actions()[-1].trigger()
            record('quit_slot_returned', worker_alive=window.service._thread.is_alive())
        def rescue():
            report['rescue_required'] = True
            record('event_loop_still_alive_after_quit')
            QApplication.instance().quit()
        QTimer.singleShot(250, close_to_tray)
        QTimer.singleShot(500, quit_action)
        QTimer.singleShot(2000, rescue)
        return window
    entry.MainWindow = create
    sys.argv = ['FileFlow', '--data-dir', str(store.path.parent)]
    result = entry.main()
    record('app_exec_returned', code=result)
raise SystemExit(result)
