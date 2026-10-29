"""Compare retaining the lightweight view against discarding its model/card.

This experiment only operates on isolated fixtures, never production state.
"""
import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtTest import QTest
from fileflow.models import Settings,Folder,Rule
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow,configure_fonts
from tools.profile_memory import measure

app=QApplication([]); app.setQuitOnLastWindowClosed(False);configure_fonts(app);tracemalloc.start(1)
report={}
with tempfile.TemporaryDirectory(prefix='FileFlow-strategies-') as temporary:
    root=Path(temporary); inbox=root/'Inbox';inbox.mkdir()
    folder=Folder(str(inbox),True,rules=[Rule('contains',f'match{n}',f'Route{n}') for n in range(6)])
    history=[dict(source=str(inbox/f'file-{n}.pdf'),destination=str(inbox/'Documents'/f'file-{n}.pdf'),status='success',detail='',time='2026-10-28T08:00:00+03:00') for n in range(200)]
    store=SettingsStore(root/'Config/settings.json');store.save(Settings([folder],history=history,tray=True))
    window=MainWindow(store);window.show();window.navigate('history',animate=False)
    window.history_table.setCurrentCell(4,0);QTest.qWait(250);window.hide();QTest.qWait(100)
    measure(app,window)  # Warm Windows API/Qt wrapper accounting before comparison.
    report['retained']=measure(app,window)
    started=time.perf_counter();window.restore();QTest.qWait(16)
    report['retained_restore_ms']=(time.perf_counter()-started)*1000
    window.hide();view=window.history_table;row=view.currentIndex().row();scroll=view.verticalScrollBar().value()
    view.replace([]);window.activity_cards=[]
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);QTest.qWait(100)
    report['released']=measure(app,window)
    window._history_dirty=True;started=time.perf_counter();window.restore()
    view.setCurrentCell(row,0);view.verticalScrollBar().setValue(scroll);QTest.qWait(16)
    report['released_restore_ms']=(time.perf_counter()-started)*1000
    report['data_preserved']=len(window.settings.history)==200 and view.count()==200
    window.quit_app()
    for _ in range(500):
        if window._closed:break
        QTest.qWait(10)
    assert window._closed and report['data_preserved']
Path(sys.argv[1]).write_text(json.dumps(report,indent=2))
