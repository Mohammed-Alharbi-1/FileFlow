import json
import threading
import time
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QLineEdit
from PySide6.QtTest import QTest
from fileflow.models import Rule
from fileflow.ui import EditDialog
from test_overhaul import window
from test_service_ui import until


def test_twenty_switch_cycles_preserve_cards_editor_filters_and_connections(window, qapp, monkeypatch, tmp_path):
    history = [dict(window.settings.history[0], source=str(tmp_path / f'file-{index}.pdf')) for index in range(200)]
    window.settings.history = history
    window.render_history(); window.navigate('history', animate=False)
    window.history_table.setCurrentCell(7, 0)
    editor = EditDialog(window, 'Unsaved', Rule('contains', 'draft', 'Unsaved'))
    editor.value.setText('typed but unsaved'); editor.destination.setText('Private/Notes')
    editor.show()
    QTest.qWait(20)
    cards = tuple(window.activity_cards); listing = window.history_table
    selected = window.selected_event(); path = window.selected_path
    scrollbar = listing.verticalScrollBar(); scrollbar.setValue(min(500, scrollbar.maximum()))
    scroll = scrollbar.value()
    widgets = len(qapp.allWidgets()); threads = len(threading.enumerate())
    monkeypatch.setattr(window, 'build', lambda: (_ for _ in ()).throw(AssertionError('visual switch rebuilt window')))
    samples = []
    for _ in range(20):
        for callback in (window.change_theme, window.change_theme, window.change_language, window.change_language):
            started = time.perf_counter(); callback(); main_ms = (time.perf_counter()-started)*1000
            QTest.qWait(16)
            samples.append(dict(main_ms=main_ms, wall_ms=(time.perf_counter()-started)*1000))
        assert tuple(window.activity_cards) == cards
        assert window.history_table is listing and window.selected_event() == selected
        assert window._section == 'history' and window.selected_path == path
        assert scrollbar.value() == scroll
        assert editor.value.text() == 'typed but unsaved' and editor.destination.text() == 'Private/Notes'
        assert len(threading.enumerate()) == threads
        assert len(qapp.allWidgets()) <= widgets+2
    # A single button click must call the saved preference exactly once.
    saves = []; original = window.store.save
    monkeypatch.setattr(window.store, 'save', lambda settings: (saves.append(True), original(settings))[-1])
    from PySide6.QtWidgets import QPushButton
    theme = next(obj for obj in window.findChildren(QPushButton) if obj.property('ffRole') == 'theme')
    theme.click(); assert len(saves) == 1
    assert window.store.load().language == window.settings.language
    (tmp_path / 'switch-latencies.json').write_text(json.dumps(samples))
    editor.close(); editor.deleteLater()
    window.search.setText('file-1'); QTest.qWait(250)
    window.status_filter.setCurrentIndex(window.status_filter.findData('success'))
    filtered = tuple(window.activity_cards)
    window.change_language(); window.change_theme()
    assert window.search.text() == 'file-1'
    assert window.status_filter.currentData() == 'success'
    assert tuple(window.activity_cards) == filtered


def test_shutdown_is_async_rejects_jobs_and_stops_owned_resources(window, qapp):
    ticks = []; timer = QTimer(); timer.setInterval(5); timer.timeout.connect(lambda: ticks.append(True)); timer.start()
    original = window.service.is_finished
    released = threading.Event()
    window.service.is_finished = lambda: released.is_set() and original()
    window.quit_app(); window.quit_app()
    assert window._shutdown_state == 'draining'
    assert not window.service.organize_now()
    assert not window.service.configure(window.settings.folders, True)
    QTest.qWait(40); assert ticks, 'GUI event loop blocked during worker cleanup'
    released.set(); until(qapp, lambda: window._closed)
    assert window.service.is_finished()
    assert not any(timer.isActive() for timer in window.findChildren(QTimer))
    timer.stop()


def test_theme_changes_real_pixels_and_language_does_not_reapply_style(window, qapp, monkeypatch):
    window.navigate('history', animate=False); QTest.qWait(20)
    initial = window.grab().toImage().pixelColor(0, 0)
    styles = []; apply = window.setStyleSheet
    monkeypatch.setattr(window, 'setStyleSheet', lambda value: (styles.append(value), apply(value))[-1])
    window.change_theme(); QTest.qWait(20)
    changed = window.grab().toImage().pixelColor(0, 0)
    assert initial.lightness() > 200 and changed.lightness() < 80
    assert len(styles) == 1
    window.change_language(); QTest.qWait(20)
    assert len(styles) == 1
    window.change_theme(); QTest.qWait(20)
    assert window.grab().toImage().pixelColor(0, 0).lightness() > 200


def test_real_windows_process_exit_relaunch_and_singleton(tmp_path):
    import os
    import pytest
    if os.name != 'nt': pytest.skip('Windows mutex/native tray integration')
    from tools.verify_lifecycle import verify
    report = verify(tmp_path / 'lifecycle.json', cycles=10)
    assert report['ok']
    assert len(report['cases']) == 19
