"""Public screenshots use fictional display paths and isolated local settings."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from fileflow.ui import MainWindow,configure_fonts
from fileflow.models import Settings,Folder,Rule
from fileflow.storage import SettingsStore

app=QApplication([]);app.setQuitOnLastWindowClosed(False);configure_fonts(app)
output=Path('docs/screenshots/public');output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='FileFlow-public-demo-') as temp:
    display=Path('C:/FileFlow Demo/Downloads')
    folder=Folder(str(display),True,rules=[Rule('contains','invoice','Work/Invoices')])
    history=[dict(source=str(display/name),destination=str(display/dest/name),status='success',detail='',time='2026-10-29T09:30:00+03:00') for name,dest in [('invoice-october.pdf','Work/Invoices'),('weekend-photo.jpg','Images'),('meeting-notes.txt','Documents')]]
    store=SettingsStore(Path(temp)/'settings.json');store.save(Settings([folder],language='en',history=history))
    window=MainWindow(store);window.resize(1180,850);window.show()
    for name,page,language,theme in [('overview-light','dashboard','en','light'),('history-dark','history','en','dark'),('rules-light','rules','en','light'),('overview-arabic','dashboard','ar','light')]:
        if window.settings.language!=language:window.change_language()
        if window.settings.theme!=theme:window.change_theme()
        window.navigate(page,animate=False)
        if page=='history':window.history_table.setCurrentCell(0,0)
        QTest.qWait(220);assert window.grab().save(str(output/(name+'.png')),'PNG')
    window.shutdown_finished.connect(app.quit);QTimer.singleShot(0,window.quit_app);app.exec();assert window._closed
