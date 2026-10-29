"""Isolated native Qt memory scenarios; no working-set trimming or GC loops."""
import sys
import time
import json
import tempfile
import tracemalloc
import argparse
import ctypes
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject, QAbstractAnimation, QTimer, Qt
from PySide6.QtWidgets import QApplication, QGraphicsEffect
from PySide6.QtTest import QTest
from fileflow.ui import MainWindow, configure_fonts
from fileflow.models import Settings, Folder, Rule
from fileflow.storage import SettingsStore
from tools.profile_switches import resources


def measure(app, window):
    result = resources(app)
    result.update(python_heap_bytes=tracemalloc.get_traced_memory()[0],
                  qobjects=len(window.findChildren(QObject)),
                  animations=len(window.findChildren(QAbstractAnimation)),
                  effects=len(window.findChildren(QGraphicsEffect)),
                  process_cpu_s=time.process_time(), elapsed_s=time.perf_counter())
    # QueryWorkingSet lists resident pages; Shared bit excludes shareable pages.
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32'); kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi'); psapi.QueryWorkingSet.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    for size in (1<<20, 4<<20, 16<<20):
        buffer = ctypes.create_string_buffer(size)
        if psapi.QueryWorkingSet(kernel.GetCurrentProcess(), buffer, size):
            words = (ctypes.c_size_t * (size // ctypes.sizeof(ctypes.c_size_t))).from_buffer(buffer)
            count = words[0]
            result['private_working_set_bytes'] = sum(not (words[i+1] & (1<<8)) for i in range(count))*4096
            break
    return result


def main(report_path=None, minutes=0):
    if report_path is None:
        parser = argparse.ArgumentParser(); parser.add_argument('report', type=Path); parser.add_argument('--minutes', type=float, default=0); args=parser.parse_args()
    else:
        from types import SimpleNamespace
        args=SimpleNamespace(report=Path(report_path),minutes=minutes)
    tracemalloc.start(1)
    app=QApplication([]); app.setQuitOnLastWindowClosed(False); configure_fonts(app)
    report={'platform':app.platformName(), 'pid':os.getpid(), 'samples':[], 'restores_ms':[]}
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='FileFlow-memory-') as temporary:
        root=Path(temporary); folders=[]
        report['fixture_name']=root.name
        for n in range(3):
            inbox=root/f'Inbox{n}'; inbox.mkdir()
            folders.append(Folder(str(inbox),True,rules=[Rule('contains',f'match{i}',f'Route{i}') for i in range(6)]))
        store=SettingsStore(root/'Config/settings.json'); store.save(Settings(folders, tray=True))
        window=MainWindow(store)
        window.setWindowTitle('FileFlow — isolated memory test')
        window.tray_icon.setToolTip(f'FileFlow isolated memory test — PID {os.getpid()}')
        window.show(); QTest.qWait(200)
        def sample(name):
            row=measure(app,window); row['scenario']=name
            report['samples'].append(row); args.report.write_text(json.dumps(report,indent=2))
        report['startup_ms']=(time.perf_counter()-started)*1000
        sample('visible-zero')
        window.hide(); QTest.qWait(200); sample('hidden-zero-disabled')
        window.restore(); window.settings.history=[dict(source=str(root/'Inbox0'/f'file-{n}.pdf'),destination=str(root/'Inbox0/Documents'/f'file-{n}.pdf'),status='success',detail='',time='2026-10-28T08:00:00+03:00') for n in range(200)]
        window.render_history(); window.navigate('history',animate=False); QTest.qWait(200); sample('visible-200')
        window.hide(); QTest.qWait(200); sample('hidden-200-disabled')
        window.settings.automatic=True; window.service.configure(folders,True)
        deadline=time.monotonic()+10
        while window._watching!=3 and time.monotonic()<deadline: QTest.qWait(20)
        assert window._watching==3
        sample('hidden-200-monitored')
        for n in range(50):
            start=time.perf_counter(); window.restore(); QTest.qWait(16)
            report['restores_ms'].append((time.perf_counter()-start)*1000)
            window.hide(); QTest.qWait(16)
            if n%10==9: sample(f'hide-restore-{n+1}')
        for n in range(100):
            (window.change_theme if n%2 else window.change_language)(); QTest.qWait(16)
            if n%20==19: sample(f'switch-{n+1}')
        # QTest.qWait can hold the GIL across long waits. Use the same native
        # event loop as production so observers/workers run normally at idle.
        background_started=time.monotonic()
        window.shutdown_finished.connect(app.quit)
        sampler=QTimer(window); sampler.setInterval(30000)
        sampler.timeout.connect(lambda:sample('sustained-background')); sampler.start()
        def finish():
            report['sustained_duration_s']=time.monotonic()-background_started
            sample('background-end')
            window.tray_icon.contextMenu().actions()[-1].trigger()
        QTimer.singleShot(0,lambda:sample('sustained-background'))
        deadline_timer=QTimer(window); deadline_timer.setSingleShot(True)
        deadline_timer.setTimerType(Qt.TimerType.PreciseTimer)
        deadline_timer.timeout.connect(finish)
        deadline_timer.start(max(0,int(args.minutes*60000)))
        app.exec()
        assert window._closed
        report['shutdown']=True; args.report.write_text(json.dumps(report,indent=2))

if __name__=='__main__': main()
