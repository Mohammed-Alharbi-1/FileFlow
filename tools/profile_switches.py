"""Real Qt event-loop benchmark; fixtures and settings are isolated, never user data."""
from pathlib import Path
import argparse
import cProfile
import gc
import io
import json
import os
import pstats
import statistics
import sys
import tempfile
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from fileflow.models import Folder, Rule, Settings
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow, configure_fonts


def resources(app):
    values = dict(widgets=len(app.allWidgets()), python_threads=len(threading.enumerate()))
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in ('peak_ws','ws','peak_pool','pool','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
        kernel = ctypes.WinDLL('kernel32'); kernel.GetCurrentProcess.restype = wintypes.HANDLE
        process = kernel.GetCurrentProcess(); info = Counters(); info.cb = ctypes.sizeof(info)
        psapi = ctypes.WinDLL('psapi'); psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(process, ctypes.byref(info), info.cb):
            values.update(working_set_mb=round(info.ws/1048576, 3), private_mb=round(info.private/1048576, 3))
        count = wintypes.DWORD(); kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        if kernel.GetProcessHandleCount(process, ctypes.byref(count)): values['handles'] = count.value
    return values


def summary(samples):
    result = {}
    for operation in sorted({s['operation'] for s in samples}):
        group = [s for s in samples if s['operation'] == operation]
        result[operation] = {}
        for key in ('main_ms', 'wall_ms'):
            numbers = sorted(s[key] for s in group)
            result[operation][key] = dict(median=round(statistics.median(numbers),2), p95=round(numbers[int((len(numbers)-1)*.95)],2), maximum=round(max(numbers),2))
    return result


def run():
    parser = argparse.ArgumentParser(); parser.add_argument('report', type=Path); parser.add_argument('--cycles', type=int, default=20); parser.add_argument('--monitoring', action='store_true'); args = parser.parse_args()
    report = {'cycles': args.cycles, 'monitoring': args.monitoring, 'measurement': 'main_ms: synchronous callback; wall_ms: request through next 16ms Qt checkpoint including paint/layout', 'scenarios': []}
    app = QApplication([]); app.setQuitOnLastWindowClosed(False); configure_fonts(app)
    with tempfile.TemporaryDirectory(prefix='FileFlow-perf-') as temporary:
        root = Path(temporary)
        def scenario(history_size):
            folders = []
            for index in range(3):
                inbox = root / f'Scenario{history_size}-Folder{index}'; inbox.mkdir()
                folders.append(Folder(str(inbox), True, rules=[Rule('contains', f'match{n}', f'Route{n}') for n in range(6)]))
            history = [dict(source=str(Path(folders[0].path) / f'file-{n}.txt'), destination=str(Path(folders[0].path) / 'Documents' / f'file-{n}.txt'), status='success', detail='', time='2026-10-28T08:00:00+03:00') for n in range(history_size)]
            store = SettingsStore(root / f'Config{history_size}' / 'settings.json'); store.save(Settings(folders, history=history, automatic=args.monitoring))
            window = MainWindow(store); window.shutdown_finished.connect(app.quit); window.show(); window.navigate('history', animate=False)
            operations = [kind for _ in range(args.cycles) for kind in ('theme','theme','language','language')]
            state = dict(history=history_size, samples=[], before=None)
            ready_deadline = time.monotonic() + 10
            def step():
                if args.monitoring and window._watching != len(folders):
                    if time.monotonic() < ready_deadline:
                        QTimer.singleShot(20, step); return
                    state['error'] = 'watchdog did not start all folders'
                    report['scenarios'].append(state); args.report.write_text(json.dumps(report, indent=2))
                    window.quit_app(); return
                state['watched_folders'] = window._watching
                if state['before'] is None: state['before'] = resources(app)
                if not operations:
                    profiler = cProfile.Profile(); profiler.enable(); window.change_theme(); window.change_language(); profiler.disable()
                    output = io.StringIO(); pstats.Stats(profiler, stream=output).sort_stats('cumulative').print_stats(30)
                    state['profile'] = output.getvalue()
                    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete); gc.collect()
                    state['after'] = resources(app); state['summary'] = summary(state['samples'])
                    report['scenarios'].append(state)
                    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
                    print(json.dumps({'history':history_size, 'summary':state['summary'], 'before':state['before'], 'after':state['after']}), flush=True)
                    window.quit_app(); return
                kind = operations.pop(0)
                if window.history_table.count(): window.history_table.setCurrentCell(0, 0)
                before = window.settings.theme if kind == 'theme' else window.settings.language
                started = time.perf_counter()
                (window.change_theme if kind == 'theme' else window.change_language)()
                main_ms = (time.perf_counter() - started) * 1000
                after = window.settings.theme if kind == 'theme' else window.settings.language
                def settled():
                    sample = dict(operation=f'{before}_to_{after}', main_ms=round(main_ms,3), wall_ms=round((time.perf_counter()-started)*1000,3))
                    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                    sample.update(resources(app)); state['samples'].append(sample)
                    if len(state['samples']) % 20 == 0: print(f'progress history={history_size} samples={len(state["samples"])}', flush=True)
                    QTimer.singleShot(10, step)
                QTimer.singleShot(16, settled)
            QTimer.singleShot(150, step)
            app.exec()
            window.service.shutdown()
            window.deleteLater(); QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete); gc.collect()
        scenario(0); scenario(200)

if __name__ == '__main__': run()
