"""Serialized worker; cooperative cancellation and observable owned-thread cleanup."""
from copy import deepcopy
from pathlib import Path
from threading import Event, Lock, Thread
import time
from PySide6.QtCore import QObject, Signal
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .engine import Activity, Organizer
from .models import Folder, validate_root
from .diagnostics import event

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, root, wake): self.root, self.wake = root, wake
    def on_any_event(self, change):
        if not change.is_directory and any(p and Path(p).parent == self.root for p in (change.src_path, getattr(change, 'dest_path', ''))): self.wake.set()

class OrganizationService(QObject):
    activity = Signal(object)
    busy = Signal(bool)
    monitoring = Signal(int)
    watched_paths = Signal(object)
    completed = Signal(int, int, bool)
    stopped = Signal()

    def __init__(self, excluded_directories=(), autostart=True):
        super().__init__()
        self.excluded_directories = tuple(Path(p).absolute() for p in excluded_directories)
        self._lock = Lock(); self._wake = Event(); self._quit = Event(); self._cancel = Event()
        self._revision = 0; self._folders = []; self._automatic = False; self._manual = False
        self._thread = Thread(target=self._run, name='FileFlow-worker', daemon=False)
        self._started = False
        if autostart: self.start()

    def start(self):
        if not self._started:
            self._started = True; self._thread.start(); event('worker_start')

    def configure(self, folders, automatic):
        if self._quit.is_set(): return False
        with self._lock:
            if self._quit.is_set(): return False
            self._cancel.set()
            self._folders = deepcopy([f for f in folders if f.confirmed and Path(f.path).absolute() not in self.excluded_directories])
            self._automatic = automatic; self._manual = False; self._revision += 1
        self._wake.set(); return True

    def organize_now(self):
        with self._lock:
            if self._quit.is_set(): return False
            self._manual = True
        self._wake.set(); return True

    def request_shutdown(self):
        self._quit.set(); self._cancel.set(); self._wake.set()
        event('worker_stop_requested')

    def is_finished(self): return not self._started or not self._thread.is_alive()

    def shutdown(self, timeout=5.0):
        """Bounded fallback. The GUI uses request_shutdown plus nonblocking polling."""
        self.request_shutdown()
        if self._started: self._thread.join(timeout)
        if not self.is_finished():
            event('worker_join_timeout', timeout_s=timeout)
            raise TimeoutError('FileFlow worker is still draining; process was not terminated')
        return True

    def _stop_observer(self, observer):
        if observer is None: return
        started = time.monotonic(); event('observer_stop_requested')
        # watchdog.stop() internally joins emitters without a timeout. Cancel/join
        # them first in bounded increments; never run these I/O calls on the GUI.
        emitters = list(observer.emitters)
        for emitter in emitters: emitter.stop()
        next_notice = started + 5
        while any(emitter.is_alive() for emitter in emitters):
            for emitter in emitters:
                if emitter.is_alive(): emitter.join(.05)
            if time.monotonic() >= next_notice:
                event('observer_cleanup_waiting', elapsed_ms=round((time.monotonic() - started) * 1000, 2)); next_notice += 5
        observer.stop()
        while observer.is_alive():
            observer.join(.1)
            if time.monotonic() >= next_notice:
                event('observer_dispatch_waiting'); next_notice += 5
        event('observer_stopped', elapsed_ms=round((time.monotonic() - started) * 1000, 2))

    def _run(self):
        observer = None; revision = -1; automatic = False; folders = []; last_scan = 0.0
        organizer = Organizer(self.activity.emit, excluded_directories=self.excluded_directories)
        try:
            while not self._quit.is_set():
                # Sleep until an event/configuration/manual request, or the
                # existing 30-second recovery scan when monitoring is active.
                timeout = max(.01, 30 - (time.monotonic() - last_scan)) if automatic else None
                changed = self._wake.wait(timeout); self._wake.clear()
                with self._lock:
                    reconfigure = revision != self._revision
                    if reconfigure:
                        revision = self._revision; folders = deepcopy(self._folders); automatic = self._automatic
                        self._cancel = Event()
                        if self._quit.is_set(): self._cancel.set()
                    cancel = self._cancel; manual = self._manual; self._manual = False
                if self._quit.is_set(): break
                if reconfigure:
                    self._stop_observer(observer); observer = None; watched = []
                    if automatic and folders and not self._quit.is_set():
                        observer = Observer()
                        # Bound raw watchdog events before starting emitters. Its
                        # dispatcher only sets our coalescing wake Event, so bursts
                        # apply backpressure instead of retaining arbitrary paths.
                        observer.event_queue.maxsize = 256
                        event('observer_initializing', folders=len(folders), queue_capacity=256)
                        for folder in folders:
                            try:
                                root = validate_root(folder.path)
                                observer.schedule(ChangeHandler(root, self._wake), str(root), recursive=False); watched.append(folder.path)
                            except (OSError, ValueError) as error: self.activity.emit(Activity(folder.path, status='error', detail=str(error)))
                        try: observer.start()
                        except OSError as error:
                            self.activity.emit(Activity('', status='error', detail=str(error)))
                            self._stop_observer(observer); observer = None; watched = []
                    self.monitoring.emit(len(watched)); self.watched_paths.emit(watched)
                    event('monitoring_changed', watched=len(watched), requested=automatic); changed = True
                if self._quit.is_set(): break
                if manual or (automatic and (changed or time.monotonic() - last_scan >= 30)):
                    self.busy.emit(True); results = []
                    for folder in folders:
                        if cancel.is_set() or self._quit.is_set(): break
                        results.extend(organizer.organize(folder, cancel))
                    last_scan = time.monotonic(); self.busy.emit(False)
                    self.completed.emit(sum(a.status == 'success' for a in results), sum(a.status != 'success' for a in results), manual)
                    # This worker frame lives while waiting for the next job.
                    # Keep no extra Activity/path references after delivery.
                    results.clear()
        except Exception as error:
            event('worker_error', error=type(error).__name__, errno=getattr(error, 'errno', None))
            self.activity.emit(Activity('', status='error', detail=str(error)))
        finally:
            try: self._stop_observer(observer)
            finally: event('worker_stopped'); self.stopped.emit()
