from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLineEdit
from PySide6.QtTest import QTest
from fileflow.controls import HoverButton
from fileflow.models import Rule
from fileflow.visuals import ActivityList, StatusPill, timestamp, category_for
from fileflow.ui import EditDialog
from test_overhaul import window


def test_history_is_activity_list_and_paths_remain_plain(window, qapp):
    from fileflow.history_view import HistoryView
    assert isinstance(window.history_table, HistoryView)
    window.navigate('history', animate=False)
    window.history_table.setCurrentCell(0, 0)
    card = window.activity_cards[0]
    assert card.expand_button.isChecked()
    QTest.qWait(50)
    assert card.height() >= card.base_height + card.reveal.maximumHeight() - 2
    fields = card.reveal.findChildren(QLineEdit)
    assert len(fields) == 2
    assert fields[0].text() == card.event['source']
    assert card.reveal.maximumHeight() > 100
    assert fields[-1].geometry().bottom() < card.reveal.height()
    for field in fields:
        assert field.layoutDirection() == Qt.LayoutDirection.LeftToRight
        field.selectAll()
        assert field.selectedText() == field.text()
        assert not any(character in field.text() for character in '\u2066\u2067\u2068\u2069')
    assert card.open_action.isEnabled() == (card.event['status'] == 'success')


def test_edit_rule_preserves_identity_order_and_disabled_state(window, qapp):
    window.navigate('rules', animate=False)
    original = window.current_folder().rules[0]
    second = Rule('contains', 'receipt', 'Receipts')
    window.current_folder().rules.append(second)
    window.enable_rule(original.id, False)
    window.render_folder()
    def accept_edit():
        editor = QApplication.activeModalWidget()
        assert isinstance(editor, EditDialog)
        editor.value.setText('md')
        editor.destination.setText('Work/Notes')
        editor.validate()
    QTimer.singleShot(20, accept_edit)
    window.edit_rule(original.id)
    rules = window.current_folder().rules
    assert [rule.id for rule in rules] == [original.id, second.id]
    assert rules[0].value == 'md' and rules[0].destination == 'Work/Notes'
    assert not rules[0].enabled
    assert window.store.load().folders[0].rules == rules


def test_contextual_folder_removal_targets_correct_folder(window, tmp_path):
    path = window.settings.folders[1].path
    marker = Path(path) / 'keep.txt'
    marker.write_bytes(b'preserve this file')
    window.navigate('folders', animate=False)
    menus = [button.menu() for button in window.folder_cards.findChildren(HoverButton) if button.menu()]
    assert len(menus) == 2
    menus[1].actions()[0].trigger()
    assert all(folder.path != path for folder in window.settings.folders)
    assert marker.read_bytes() == b'preserve this file'


def test_history_expansion_uses_real_native_animation(window, qapp, monkeypatch):
    monkeypatch.setattr('fileflow.visuals.motion_duration', lambda: 180)
    window.navigate('history', animate=False)
    window.history_table.setCurrentCell(0, 0)
    card = window.activity_cards[0]
    card.expand_button.setChecked(False); QTest.qWait(240)
    base = card.item.sizeHint().height()
    QTest.mouseClick(card.expand_button, Qt.MouseButton.LeftButton)
    assert card.reveal_animation.duration() == 180
    QTest.qWait(240)
    assert card.reveal.maximumHeight() > 0
    assert card.item.sizeHint().height() > base
    assert card.height() >= card.base_height + card.reveal.maximumHeight() - 2
    QTest.mouseClick(card.expand_button, Qt.MouseButton.LeftButton)
    QTest.qWait(240)
    assert card.reveal.maximumHeight() == 0


def test_locale_and_icons_have_meaningful_categories(window):
    sample = '2026-10-28T14:23:00+03:00'
    assert timestamp(sample, 'ar') != timestamp(sample, 'en')
    assert 'Oct' in timestamp(sample, 'en')
    assert category_for('picture.PNG') == 'Images'
    assert category_for('unknown.bin') == 'Other Files'
    assert isinstance(window.monitor_label, StatusPill)
    assert window.state_label is window.monitor_label
    assert window.organize_button.maximumWidth() == 164


def test_small_activity_cards_and_balanced_category_grid(window, qapp):
    window.resize(820, 600)
    window.navigate('history', animate=False)
    qapp.processEvents()
    for card in window.activity_cards:
        assert card.open_action.geometry().right() < card.width()
        assert card.name_button.geometry().right() <= card.name_button.parentWidget().width()
    window.navigate('dashboard', animate=False)
    grid = next(layout for widget in window.detail.findChildren(__import__('PySide6.QtWidgets', fromlist=['QWidget']).QWidget) if (layout := widget.layout()) and hasattr(layout, 'columnCount'))
    assert grid.itemAtPosition(3, 0) is grid.itemAtPosition(3, 1)
    from PySide6.QtWidgets import QLabel
    caption = window.findChild(QLabel, 'folderCaption')
    assert caption.geometry().right() < caption.parentWidget().width()


def test_activity_double_click_preserves_explorer_interaction(window, qapp, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    calls = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: calls.append(url.toLocalFile()) or True)
    window.navigate('history', animate=False)
    row = next(i for i, event in enumerate(window._history_rows) if event['status'] == 'success')
    window.history_table.setCurrentCell(row, 0)
    success = next(card for card in window.activity_cards if card.event['status'] == 'success')
    QTest.mouseDClick(success.name_button, Qt.MouseButton.LeftButton)
    assert Path(calls[-1]) == Path(success.event['destination']).parent
