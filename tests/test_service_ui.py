from pathlib import Path
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from fileflow.engine import Organizer
from fileflow.models import Folder
from fileflow.service import OrganizationService
from fileflow.storage import SettingsStore
from fileflow.ui import EditDialog, MainWindow


def until(qapp, predicate, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        qapp.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    assert predicate(), "Timed out waiting for background work"


def fast_service(monkeypatch):
    import fileflow.service as module
    monkeypatch.setattr(module, "Organizer", lambda callback, **kwargs: Organizer(callback, interval=.01, quiet=.04, timeout=.3, **kwargs))


def test_watchdog_moves_new_files_and_stops_when_disabled(tmp_path, qapp, monkeypatch):
    fast_service(monkeypatch)
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    service = OrganizationService()
    watched = []
    service.monitoring.connect(watched.append)
    try:
        folder = Folder(str(inbox), True)
        service.configure([folder], True)
        until(qapp, lambda: watched and watched[-1] == 1)
        (inbox / "new.pdf").write_bytes(b"live monitoring")
        until(qapp, lambda: (inbox / "Documents/new.pdf").exists())
        service.configure([folder], False)
        until(qapp, lambda: watched[-1] == 0)
        (inbox / "untouched.txt").write_bytes(b"manual")
        QTest.qWait(200)
        assert (inbox / "untouched.txt").exists()
        service.organize_now()
        until(qapp, lambda: (inbox / "Documents/untouched.txt").exists())
    finally:
        service.shutdown()
    assert not service._thread.is_alive()


def test_disabling_cancels_pending_stability_wait(tmp_path, qapp):
    source = tmp_path / "pending.txt"
    source.write_bytes(b"pending")
    service = OrganizationService()
    busy = []
    service.busy.connect(busy.append)
    try:
        folder = Folder(str(tmp_path), True)
        service.configure([folder], True)
        until(qapp, lambda: busy and busy[-1])
        service.configure([folder], False)
        until(qapp, lambda: busy[-1] is False)
        assert source.exists()
        assert not (tmp_path / "Documents").exists()
    finally:
        service.shutdown()


def test_ui_explicit_setup_rules_history_modes_and_removal(tmp_path, qapp, monkeypatch):
    fast_service(monkeypatch)
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    store = SettingsStore(tmp_path / "settings" / "settings.json")
    window = MainWindow(store)
    window.show()
    qapp.processEvents()
    try:
        assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft
        assert not window.organize_button.isEnabled()
        window.change_theme()
        assert window.settings.theme == "dark"
        assert not store.path.exists()
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_: str(inbox))

        def confirm_setup():
            dialog = QApplication.activeModalWidget()
            assert isinstance(dialog, QMessageBox)
            for action in dialog.buttons():
                if dialog.buttonRole(action) == QMessageBox.ButtonRole.AcceptRole:
                    action.click()
                    return
            raise AssertionError("No setup action")

        QTimer.singleShot(20, confirm_setup)
        QTest.mouseClick(window.add_folder_button, Qt.MouseButton.LeftButton)
        assert store.path.exists()
        assert not window.settings.automatic
        assert list(inbox.iterdir()) == []
        assert window.organize_button.isEnabled()

        def fill_rule():
            dialog = QApplication.activeModalWidget()
            assert isinstance(dialog, EditDialog)
            dialog.kind.setCurrentIndex(1)
            dialog.value.setText("invoice")
            dialog.destination.setText("Work/Invoices")
            dialog.validate()

        QTimer.singleShot(20, fill_rule)
        window.add_rule()
        rule = window.current_folder().rules[0]
        assert rule.destination == "Work/Invoices"
        window.enable_rule(rule.id, False)
        assert not window.current_folder().rules[0].enabled
        window.enable_rule(rule.id, True)
        source = inbox / "invoice.pdf"
        source.write_bytes(b"real content")
        QTest.mouseClick(window.organize_button, Qt.MouseButton.LeftButton)
        until(qapp, lambda: window.history_table.rowCount() == 1)
        assert (inbox / "Work/Invoices/invoice.pdf").read_bytes() == b"real content"
        assert window.settings.history[0]["status"] == "success"
        window.history_table.setCurrentCell(0, 0)
        qapp.processEvents()
        assert window.open_button.isEnabled()
        window.change_language()
        assert window.layoutDirection() == Qt.LayoutDirection.LeftToRight
        assert window.organize_button.text() in ("Organize now", "Organizing…")
        window.remove_rule(rule.id)
        assert window.current_folder().rules == []
        window.remove_folder()
        assert window.settings.folders == []
        assert (inbox / "Work/Invoices/invoice.pdf").exists()
    finally:
        window.quit_app()
        qapp.processEvents()


def test_cancel_setup_never_writes(tmp_path, qapp):
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    source = inbox / "stay.txt"
    source.write_bytes(b"no consent")
    store = SettingsStore(tmp_path / "config/settings.json")
    window = MainWindow(store)
    window.show()
    try:
        QTimer.singleShot(20, lambda: QApplication.activeModalWidget().reject())
        assert not window.setup_folder(str(inbox))
        assert not store.path.exists()
        assert list(inbox.iterdir()) == [source]
    finally:
        window.quit_app()


def test_bad_config_survives_ui_close_without_setup(tmp_path, qapp, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning", lambda *_: None)
    window = MainWindow(SettingsStore(path))
    qapp.processEvents()
    window.change_theme()
    window.quit_app()
    qapp.processEvents()
    assert path.read_text() == "broken"


def test_app_settings_folder_cannot_be_selected(tmp_path, qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *_: None)
    window = MainWindow(SettingsStore(tmp_path / "settings.json"))
    try:
        assert not window.setup_folder(str(tmp_path))
        assert window.settings.folders == []
        assert list(tmp_path.iterdir()) == []
    finally:
        window.quit_app()
