from datetime import datetime, timedelta
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QPoint, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QTest
from fileflow.controls import Switch, CheckBox, motion_duration
from fileflow.models import Folder, Rule, Settings
from fileflow.storage import SettingsStore
from fileflow.ui import MainWindow
from test_service_ui import until, fast_service


@pytest.fixture
def window(tmp_path, qapp, monkeypatch):
    monkeypatch.setenv('FILEFLOW_REDUCED_MOTION', '1')
    root = tmp_path / 'Inbox'
    root.mkdir()
    other = tmp_path / 'Other'
    other.mkdir()
    target = root / 'Documents'
    target.mkdir()
    settings = Settings([Folder(str(root), True, rules=[Rule('extension', 'txt', 'Notes')]), Folder(str(other), True)])
    now = datetime.now().astimezone()
    for name, status, date, base in [('invoice.pdf', 'success', now, root), ('locked.txt', 'error', now, root), ('old.zip', 'success', now - timedelta(days=20), other)]:
        settings.history.append(dict(source=str(base / name), destination=str(target / name) if status == 'success' else '', status=status, detail='Access denied {test}' if status == 'error' else '', time=date.isoformat(timespec='seconds')))
    store = SettingsStore(tmp_path / 'Config/settings.json')
    store.save(settings)
    instance = MainWindow(store)
    instance.show()
    qapp.processEvents()
    yield instance
    instance.quit_app()
    until(qapp, lambda: instance._closed)
    instance.deleteLater()


@pytest.mark.parametrize('control_type', [Switch, CheckBox])
@pytest.mark.parametrize('rtl', [False, True])
def test_full_hit_target_keyboard_focus_disabled_and_visual_state(qapp, control_type, rtl, monkeypatch):
    monkeypatch.setenv('FILEFLOW_REDUCED_MOTION', '1')
    control = control_type('A label with a wide click target')
    control.resize(420, 44)
    control.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
    control.show()
    qapp.processEvents()
    before = control.grab().toImage()
    QTest.mouseClick(control, Qt.MouseButton.LeftButton, pos=QPoint(210, 22))
    assert control.isChecked()
    assert control.position == 1
    assert control.grab().toImage() != before
    control.setFocus()
    QTest.keyClick(control, Qt.Key.Key_Space)
    assert not control.isChecked()
    control.setEnabled(False)
    QTest.mouseClick(control, Qt.MouseButton.LeftButton)
    assert not control.isChecked()
    control.close()


def test_navigation_history_filters_and_operation_details(window, qapp):
    QTest.mouseClick(window.nav_buttons['history'], Qt.MouseButton.LeftButton)
    assert window._section == 'history'
    assert window.stack.currentWidget() is window.pages['history']
    assert window.history_table.rowCount() == 3
    window.status_filter.setCurrentIndex(window.status_filter.findData('error'))
    assert window.history_table.rowCount() == 1
    window.history_table.setCurrentCell(0, 0)
    assert 'Access denied {test}' in window.history_details.text()
    assert not window.open_button.isEnabled()
    window.status_filter.setCurrentIndex(0)
    window.date_filter.setCurrentIndex(window.date_filter.findData('today'))
    assert window.history_table.rowCount() == 2
    window.date_filter.setCurrentIndex(0)
    window.folder_history(window.settings.folders[1].path)
    assert window.history_table.rowCount() == 1
    assert 'old.zip' in window.history_table.item(0, 0).text()
    window.history_folder.setCurrentIndex(0)
    window.search.setText('INVOICE')
    until(qapp, lambda: window.history_table.rowCount() == 1 and 'invoice' in window.history_table.item(0, 0).text())
    window.search.setText('does-not-exist')
    until(qapp, lambda: window.history_table.rowCount() == 0)
    assert window.history_empty.isVisible()


def test_native_explorer_actions_and_missing_destination(window, monkeypatch):
    calls = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: calls.append(url.toLocalFile()) or True)
    window.navigate('history')
    success = next(event for event in window._history_rows if event['status'] == 'success')
    window.open_event(success)
    assert Path(calls[-1]) == Path(success['destination']).parent
    missing = dict(success, destination=str(Path(success['destination']).parent / 'missing' / 'file.pdf'))
    count = len(calls)
    window.open_event(missing)
    assert len(calls) == count
    assert window.toast.isVisible()
    assert window.toast.property('warning') is True
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda _: False)
    window.open_event(success)
    assert window.state_label.text() == window.t('missing')


def test_rule_mouse_keyboard_language_theme_and_reopen(window, qapp):
    window.navigate('rules')
    rule = window.current_folder().rules[0]
    control = window.rule_controls[rule.id]
    QTest.mouseClick(control, Qt.MouseButton.LeftButton, pos=control.rect().center())
    assert not window.current_folder().rules[0].enabled
    window.change_language()
    assert window._section == 'rules'
    control = window.rule_controls[rule.id]
    assert not control.isChecked()
    control.setFocus()
    QTest.keyClick(control, Qt.Key.Key_Space)
    assert window.current_folder().rules[0].enabled
    window.change_theme()
    assert window.rule_controls[rule.id].property('dark') is True
    window.enable_rule(rule.id, False)
    window.quit_app()
    reopened = MainWindow(window.store)
    try:
        assert not reopened.current_folder().rules[0].enabled
        assert len(reopened.settings.history) == 3
        assert reopened.settings.language == 'en'
        assert reopened.settings.theme == 'dark'
    finally:
        reopened.quit_app()


def test_real_watcher_toggle_and_immediate_manual_feedback(window, qapp, monkeypatch):
    fast_service(monkeypatch)
    # Existing service has already created its organizer; real production quiet window is exercised.
    QTest.mouseClick(window.auto, Qt.MouseButton.LeftButton, pos=window.auto.rect().center())
    until(qapp, lambda: window._watching == 2)
    assert window.settings.automatic and window.auto.isChecked()
    QTest.mouseClick(window.auto, Qt.MouseButton.LeftButton, pos=window.auto.rect().center())
    until(qapp, lambda: window._watching == 0)
    assert not window.settings.automatic
    source = Path(window.selected_path) / 'manual.pdf'
    source.write_bytes(b'isolated payload')
    QTest.mouseClick(window.organize_button, Qt.MouseButton.LeftButton)
    assert not window.organize_button.isEnabled()
    assert window._busy
    until(qapp, lambda: window.organize_button.isEnabled(), timeout=8)
    assert not source.exists()
    assert window.toast.message.text() == window.t('done', n=1, e=0)


@pytest.mark.parametrize('language', ['ar', 'en'])
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_small_window_scroll_navigation_and_long_names(window, qapp, language, theme):
    window.settings.language, window.settings.theme = language, theme
    window.build()
    window.resize(820, 600)
    qapp.processEvents()
    scroll = window.scrolls['dashboard']
    assert scroll.verticalScrollBar().maximum() > 0
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QWheelEvent
    wheel = QWheelEvent(QPointF(60, 60), QPointF(scroll.viewport().mapToGlobal(QPoint(60, 60))), QPoint(), QPoint(0, -120), Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    qapp.sendEvent(scroll.viewport(), wheel)
    assert scroll.verticalScrollBar().value() > 0
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    qapp.processEvents()
    assert scroll.verticalScrollBar().value() > 0
    for section in window.sections:
        QTest.mouseClick(window.nav_buttons[section], Qt.MouseButton.LeftButton)
        assert window._section == section
    assert window.stack.width() > 500
    window.navigate('history')
    assert window.history_table.isVisible()
    assert window.open_button.geometry().bottom() < window.pages['history'].height()


def test_reduced_motion_and_completion_only_toast(window, monkeypatch):
    monkeypatch.setenv('FILEFLOW_REDUCED_MOTION', '1')
    assert motion_duration() == 0
    window.start_organization()
    assert not window.toast.isVisible()
    window.on_completed(4, 1, True)
    assert window.toast.message.text() == window.t('done', n=4, e=1)
    assert window.toast.property('warning')


def test_monitor_updates_keep_rule_focus_and_failed_save_rolls_back(window, qapp, monkeypatch):
    window.navigate('rules')
    rule = window.current_folder().rules[0]
    control = window.rule_controls[rule.id]
    control.setFocus()
    window.on_watched_paths([])
    assert window.rule_controls[rule.id] is control
    def failed(*_):
        raise PermissionError('isolated save failure')
    monkeypatch.setattr(window.store, 'save', failed)
    previous = window.settings.theme
    window.change_theme()
    assert window.settings.theme == previous
    window.toggle_auto(True)
    assert not window.auto.isChecked()
    assert not window.settings.automatic


def test_retained_200_records_persist_and_filter_after_restart(window, qapp):
    import time
    prototype = window.settings.history[0]
    window.settings.history = [dict(prototype, source=str(Path(prototype['source']).parent / f'file-{n}.pdf')) for n in range(200)]
    window.persist()
    start = time.monotonic()
    window.render_history()
    assert window.history_table.rowCount() == 200
    assert time.monotonic() - start < 2.0
    window.change_language()
    assert window.history_table.rowCount() == 200
    assert len(window.store.load().history) == 200


def test_folder_actions_and_filter_survive_language_and_theme(window, qapp):
    path = window.settings.folders[1].path
    window.folder_rules(path)
    assert window.current_folder().path == path
    assert window._section == 'rules'
    window.folder_history(path)
    assert window.history_table.rowCount() == 1
    window.change_language()
    window.change_theme()
    assert window._section == 'history'
    assert window.history_folder.currentData() == path
    assert window.history_table.rowCount() == 1


def test_long_arabic_folder_and_visible_action_paint(window, qapp, tmp_path):
    from fileflow.controls import HoverButton
    from PySide6.QtGui import QColor
    point = window.organize_button.mapTo(window, window.organize_button.rect().center())
    pixel = QColor(window.grab().toImage().pixel(point))
    assert pixel.blue() > pixel.red() + 20
    root = tmp_path / ('مجلد_طويل_' * 12)
    root.mkdir()
    window.settings.folders = [Folder(str(root), True)]
    window.selected_path = str(root)
    window.resize(820, 600)
    window.build()
    window.navigate('folders', animate=False)
    qapp.processEvents()
    assert window.folder_cards.width() <= window.stack.width()
    window.navigate('dashboard', animate=False)
    qapp.processEvents()
    for action in window.detail.findChildren(HoverButton):
        assert action.geometry().right() <= action.parentWidget().width()


def test_tray_preference_close_restore_and_quit_contract(window, qapp, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, 'isSystemTrayAvailable', lambda: True)
    visible = []
    monkeypatch.setattr(window.tray_icon, 'setVisible', visible.append)
    window.navigate('settings')
    window.tray_check.setEnabled(True)
    QTest.mouseClick(window.tray_check, Qt.MouseButton.LeftButton, pos=window.tray_check.rect().center())
    assert window.settings.tray
    assert window.store.load().tray
    assert visible[-1] is True
    window.close()
    assert not window.isVisible()
    assert not window._closed
    window.restore()
    assert window.isVisible()
    window.quit_app()
    until(qapp, lambda: window._closed)
