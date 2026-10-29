"""Isolate the legacy per-record widget cost using the retained card class.

This is a component experiment, not a substitute for matched EXE measurements.
"""
import json
from pathlib import Path
import sys
import tempfile
import tracemalloc
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication,QListWidgetItem
from PySide6.QtTest import QTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fileflow.models import Settings,Folder
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow,configure_fonts
from fileflow.visuals import ActivityCard,ActivityList
from tools.profile_memory import measure

tracemalloc.start(10);app=QApplication([]);app.setQuitOnLastWindowClosed(False);configure_fonts(app)
with tempfile.TemporaryDirectory(prefix='FileFlow-history-allocation-') as temporary:
    root=Path(temporary);inbox=root/'Inbox';inbox.mkdir()
    records=[dict(source=str(inbox/f'file-{n}.pdf'),destination=str(inbox/'Documents'/f'file-{n}.pdf'),status='success',detail='',time='2026-10-28T08:00:00+03:00') for n in range(200)]
    store=SettingsStore(root/'Config/settings.json');store.save(Settings([Folder(str(inbox),True)],history=records))
    window=MainWindow(store);window.show();window.navigate('history',animate=False);QTest.qWait(100)
    measure(app,window)
    before=measure(app,window);snapshot=tracemalloc.take_snapshot()
    legacy=ActivityList();legacy.setObjectName('activityList');window.page_layouts['history'].addWidget(legacy)
    window.history_table.hide()
    for event in records:
        item=QListWidgetItem(Path(event['source']).name);item.setData(Qt.ItemDataRole.UserRole,event);legacy.addItem(item)
        legacy.setItemWidget(item,ActivityCard(window,event,item,legacy))
    QTest.qWait(100);after=measure(app,window)
    differences=tracemalloc.take_snapshot().compare_to(snapshot,'lineno')
    report=dict(before=before,with_200_legacy_cards=after,
                python_allocation_deltas=[dict(location=str(stat.traceback),bytes=stat.size_diff,count=stat.count_diff) for stat in differences[:15]],
                interpretation='Adds legacy widgets alongside a hidden lightweight view; includes trace overhead; not exact Qt native allocation accounting')
    window.shutdown_finished.connect(app.quit);QTimer.singleShot(0,window.quit_app);app.exec();assert window._closed
Path(sys.argv[1]).write_text(json.dumps(report,indent=2),encoding='utf-8')
