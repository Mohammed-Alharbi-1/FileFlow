"""Render native Qt screenshots from actual moves in isolated temporary folders."""
from pathlib import Path
import argparse
import os
import sys
import tempfile
from threading import Thread, Event
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ['FILEFLOW_REDUCED_MOTION'] = '1'  # Capture settled states, not transition frames.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from fileflow.engine import Organizer
from fileflow.models import Folder, Rule, Settings
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow, brand_icon, configure_fonts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--icon-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    app = QApplication([])
    configure_fonts(app)
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    assert brand_icon(256).pixmap(256, 256).save(str(assets / "fileflow.ico"))
    if args.icon_only:
        return
    output = root / 'docs' / 'screenshots'
    output.mkdir(parents=True, exist_ok=True)
    baseline = root / 'dist/FileFlow-1.1.0-win-x64.zip'
    before = output / 'before-v1.1'
    if baseline.exists() and not before.exists():
        before.mkdir()
        with zipfile.ZipFile(baseline) as archive:
            lookup = {name.replace('\\', '/'): name for name in archive.namelist()}
            for name in ('fileflow-en-dark.png', 'history-ar-dark.png', 'rules-ar-dark.png'):
                (before / name).write_bytes(archive.read(lookup['FileFlow/docs/screenshots/' + name]))
    with tempfile.TemporaryDirectory(prefix="FileFlow-preview-") as temporary:
        temp = Path(temporary)
        inbox = temp / "Inbox"
        inbox.mkdir()
        folder = Folder(str(inbox), True, rules=[Rule("contains", "invoice", "Work/Invoices")])
        for name in ("invoice-october.pdf", "weekend-photo.jpg", "project-notes.txt"):
            (inbox / name).write_bytes(b"Isolated test content, not real media.")
        results = Organizer(interval=.005, quiet=.01).organize(folder)
        assert len(results) == 3 and all(a.status == "success" for a in results)
        if os.name == 'nt':
            with (inbox / 'ملف قيد الاستخدام.txt').open('wb') as writer:
                writer.write(b'Isolated locked-file QA'); writer.flush()
                locked = Organizer(interval=.005, quiet=.01).organize(folder)
                assert len(locked) == 1 and locked[0].status == 'error'
                results.extend(locked)
        second = temp / 'مراجعة العمل'; second.mkdir()
        growing = second / 'pending.pdf'; growing.write_bytes(b'Isolated download QA')
        stop = Event()
        def write_chunks():
            while not stop.wait(.005):
                with growing.open('ab') as stream: stream.write(b'chunk')
        thread = Thread(target=write_chunks); thread.start()
        try:
            deferred = Organizer(interval=.005, quiet=.04, timeout=.08).organize(Folder(str(second), True))
            assert deferred[0].status == 'deferred'
            results.extend(deferred)
        finally:
            stop.set(); thread.join()
        store = SettingsStore(temp / "config/settings.json")
        store.save(Settings([folder, Folder(str(second), True)], history=[a.to_dict() for a in results]))
        window = MainWindow(store)
        window.show()
        app.processEvents(); QTest.qWait(80)
        assert window.grab().save(str(output / "fileflow-ar-light.png"))
        window.settings.theme = "dark"
        window.build()
        app.processEvents(); QTest.qWait(80)
        assert window.grab().save(str(output / "fileflow-ar-dark.png"))
        window.change_language()
        app.processEvents(); QTest.qWait(80)
        assert window.grab().save(str(output / "fileflow-en-dark.png"))
        for language in ('ar', 'en'):
            for theme in ('light', 'dark'):
                window.settings.language, window.settings.theme = language, theme
                window.build()
                window.navigate('history', animate=False)
                window.history_table.setCurrentCell(0, 0)
                app.processEvents(); QTest.qWait(80)
                assert window.grab().save(str(output / f'history-{language}-{theme}.png'))
        window.settings.language = 'ar'
        window.build()
        window.navigate('rules', animate=False)
        app.processEvents(); QTest.qWait(80)
        assert window.grab().save(str(output / 'rules-ar-dark.png'))
        window.navigate('folders', animate=False)
        window.resize(820, 600)
        app.processEvents(); QTest.qWait(80)
        assert window.grab().save(str(output / 'folders-ar-small.png'))
        matrix = output / 'v1.2'; matrix.mkdir(exist_ok=True)
        for language in ('ar', 'en'):
            for theme in ('light', 'dark'):
                for width, height in ((820, 600), (1180, 900)):
                    window.settings.language, window.settings.theme = language, theme
                    window.resize(width, height); window.build()
                    for section in window.sections:
                        window.navigate(section, animate=False)
                        if section == 'history': window.history_table.setCurrentCell(0, 0)
                        app.processEvents(); QTest.qWait(60)
                        assert window.grab().save(str(matrix / f'{section}-{language}-{theme}-{width}.png'))
        window.settings.language, window.settings.theme = 'ar', 'light'
        window.build(); window.resize(820, 600); window.navigate('history', animate=False)
        window.search.setText('no-match-for-qa'); QTest.qWait(180)
        assert window.grab().save(str(matrix / 'history-empty-ar-light-820.png'))
        window.quit_app()
        import time
        deadline = time.monotonic() + 5
        while not window._closed and time.monotonic() < deadline:
            app.processEvents(); QTest.qWait(10)
        assert window._closed
    print(output)


if __name__ == "__main__":
    main()
