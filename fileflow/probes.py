"""Opt-in diagnostics run the real entry point, tray QAction and owned worker.

Only accepts a harness-created settings directory carrying an explicit marker.
No production folder or settings may be used for this diagnostic.
"""
import json
from pathlib import Path
from threading import Event, enumerate as threads
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QSystemTrayIcon


class LifecycleProbe:
    def __init__(self, window, scenario, report):
        self.window, self.scenario, self.path = window, scenario, report
        self.started = time.perf_counter()
        self.report = dict(scenario=scenario, tray_available=QSystemTrayIcon.isSystemTrayAvailable(), events=[], rescue=False)
        self.root = window.store.path.parent.parent
        if not (self.root / 'FILEFLOW_ISOLATED_TEST').is_file():
            window.quit_app()
            raise ValueError('Lifecycle diagnostics require the isolated-test marker')
        self.inbox = self.root / 'Inbox'
        if len(window.settings.folders) != 1 or Path(window.settings.folders[0].path) != self.inbox:
            window.quit_app()
            raise ValueError('Lifecycle diagnostics require exactly the isolated Inbox')
        self.original_rename = None
        if scenario == 'active':
            from . import engine
            self.entered = Event()
            self.original_rename = engine.rename_no_replace
            def delayed(*args):
                self.entered.set()
                time.sleep(.3)  # Test-only gate within an already authorized safe move.
                return self.original_rename(*args)
            engine.rename_no_replace = delayed
        self.note('started')
        self.poll = QTimer(window); self.poll.setInterval(20); self.poll.timeout.connect(self.step); self.poll.start()
        QTimer.singleShot(12000, self.rescue)

    def note(self, name, **fields):
        self.report['events'].append(dict(event=name, seconds=round(time.perf_counter()-self.started, 4), **fields))
        self.path.write_text(json.dumps(self.report, indent=2), encoding='utf-8')

    def quit(self, tray=False):
        self.note('quit_requested', worker_alive=not self.window.service.is_finished())
        self.poll.stop()
        if tray: self.window.tray_icon.contextMenu().actions()[-1].trigger()
        else: self.window.quit_app()

    def step(self):
        w = self.window
        elapsed = time.perf_counter()-self.started
        if elapsed < .2: return
        if self.scenario in ('tray', 'background') and not getattr(self, 'hidden', False):
            w.close(); self.hidden = True
            self.note('close_to_tray', visible=w.isVisible(), state=w._shutdown_state)
            if self.scenario == 'background': (self.inbox / 'background.txt').write_bytes(b'background proof')
            return
        if self.scenario == 'tray': self.quit(tray=True)
        elif self.scenario == 'close':
            self.note('window_close'); self.poll.stop(); w.close()
        elif self.scenario == 'background':
            if (self.inbox / 'Documents/background.txt').exists():
                self.note('background_move', visible=w.isVisible(), watching=w._watching)
                self.quit(tray=True)
        elif self.scenario == 'monitoring':
            if w._watching: self.note('watching', count=w._watching); self.quit()
        elif self.scenario == 'pending':
            if w._busy: self.note('pending_stability'); self.quit()
        elif self.scenario == 'active':
            if self.entered.is_set(): self.note('move_in_flight'); self.quit()
        elif self.scenario == 'hold' and elapsed > 4: self.quit()

    def rescue(self):
        self.report['rescue'] = True
        self.note('cooperative_rescue')
        self.window.quit_app()  # No process killing, even on a failed test.

    def finish(self, code):
        if self.original_rename:
            from . import engine
            engine.rename_no_replace = self.original_rename
        self.report.update(exit_code=code, shutdown=self.window._shutdown_state,
                           worker_finished=self.window.service.is_finished(), threads=[t.name for t in threads()])
        source = self.inbox / 'proof.txt'; destination = self.inbox / 'Documents/proof.txt'
        self.report['proof_preserved'] = (source.exists() and source.read_bytes() == b'file safety proof') or (destination.exists() and destination.read_bytes() == b'file safety proof')
        self.report['proof_moved'] = destination.exists()
        self.note('event_loop_returned')
