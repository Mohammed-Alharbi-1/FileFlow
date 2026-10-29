"""Capture the unchanged visual design after in-place palette/locale updates."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from fileflow.models import Settings, Folder
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow, configure_fonts

app = QApplication([]); app.setQuitOnLastWindowClosed(False); configure_fonts(app)
output = Path(sys.argv[1]); output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='FileFlow-visual-hotfix-') as temporary:
    root = Path(temporary); inbox = root / 'Inbox'; inbox.mkdir()
    history = [dict(source=str(inbox/f'receipt-{n}.pdf'), destination=str(inbox/f'Documents/receipt-{n}.pdf'), status='success' if n%3 else 'error', detail='', time='2026-10-28T08:00:00+03:00') for n in range(200)]
    store = SettingsStore(root/'Config/settings.json'); store.save(Settings([Folder(str(inbox),True)], history=history))
    window = MainWindow(store); window.resize(1180,850); window.show(); window.navigate('history', animate=False)
    for language, theme in [('ar','light'),('ar','dark'),('en','dark'),('en','light')]:
        if window.settings.language != language: window.change_language()
        if window.settings.theme != theme: window.change_theme()
        QTest.qWait(150)
        window.grab().save(str(output/f'history-{language}-{theme}.png'))
    window.quit_app()
    for _ in range(500):
        if window._closed: break
        QTest.qWait(10)
    assert window._closed
