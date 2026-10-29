from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QUrl, QTimer, QLocale, QPropertyAnimation, QEasingCurve, Signal, QAbstractAnimation, QCoreApplication, QEvent
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSystemTrayIcon, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from .workspace import Workspace
from .controls import HoverButton
from .visuals import FilterCombo
from .engine import Activity
from .i18n import tr
from .models import CATEGORIES, Folder, Rule, Settings, validate_destination, validate_root
from .service import OrganizationService
from .storage import SettingsStore
from .diagnostics import event as diagnostic
from .localization import bind, role
import time


def brand_icon(size=64):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#3478f6"))
    painter.drawRoundedRect(0, 0, size, size, size * .26, size * .26)
    painter.scale(size / 64, size / 64)
    painter.setBrush(QColor("#f1f7e7"))
    path = QPainterPath()
    path.moveTo(17, 16)
    path.lineTo(48, 16)
    path.lineTo(48, 25)
    path.lineTo(27, 25)
    path.lineTo(27, 31)
    path.lineTo(43, 31)
    path.lineTo(43, 40)
    path.lineTo(27, 40)
    path.lineTo(27, 49)
    path.lineTo(17, 49)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def configure_fonts(app):
    # Qt's offscreen platform does not discover Windows fonts automatically.
    import os
    if app.platformName() == "offscreen" and os.name == "nt":
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "tahoma.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
    app.setFont(QFont("Segoe UI", 10))


def label(text, name="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return bind(widget, text)


def button(text, callback, name=""):
    widget = HoverButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return bind(widget, text, role(callback))


class EditDialog(QDialog):
    def __init__(self, parent, destination, rule=None):
        super().__init__(parent)
        self.t = parent.t
        self.rule = rule
        self.setWindowTitle(self.t("add_rule") if rule else self.t("edit"))
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        form = QFormLayout()
        form.setSpacing(14)
        if rule:
            self.kind = FilterCombo()
            for key in ("extension", "contains"):
                self.kind.addItem(self.t(key), key)
            self.kind.setCurrentIndex(0 if rule.kind == "extension" else 1)
            self.value = QLineEdit(rule.value)
            form.addRow(self.t("rules"), self.kind)
            form.addRow(self.t("value"), self.value)
        self.destination = QLineEdit(destination)
        self.destination.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        form.addRow(self.t("destination"), self.destination)
        layout.addLayout(form)
        layout.addWidget(label(self.t("relative_hint"), "muted", True))
        self.error = label("", "error", True)
        layout.addWidget(self.error)
        actions = QDialogButtonBox()
        actions.addButton(self.t("save"), QDialogButtonBox.ButtonRole.AcceptRole)
        actions.addButton(self.t("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        actions.accepted.connect(self.validate)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)
        self.setProperty('ffTitleKey', 'add_rule' if rule else 'edit')
        for caption in self.findChildren(QLabel): bind(caption, caption.text())
        for caption in actions.buttons(): bind(caption, caption.text())
        self.fade = QPropertyAnimation(self, b'windowOpacity', self)
        self.fade.setDuration(__import__('fileflow.controls', fromlist=['motion_duration']).motion_duration())
        self.fade.setStartValue(.8); self.fade.setEndValue(1.0)

    def showEvent(self, event):
        super().showEvent(event)
        self.fade.start()

    def validate(self):
        try:
            self.result_destination = validate_destination(self.destination.text())
            if self.rule:
                self.result_rule = Rule(self.kind.currentData(), self.value.text().strip(), self.result_destination)
                self.result_rule.validate()
            self.accept()
        except ValueError as error:
            self.error.setText(self.t("rule_error" if str(error) == "rule" else "destination_error"))


class MainWindow(Workspace, QMainWindow):
    shutdown_finished = Signal()
    def __init__(self, store: SettingsStore | None = None):
        super().__init__()
        self.store = store or SettingsStore()
        self.load_error = ""
        try:
            self.settings = self.store.load()
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.settings = Settings()
            self.load_error = str(error)
        self.service = OrganizationService(excluded_directories=[self.store.path.parent], autostart=False)
        self.service.activity.connect(self.on_activity)
        self.service.busy.connect(self.on_busy)
        self.service.monitoring.connect(self.on_monitoring)
        self.service.watched_paths.connect(self.on_watched_paths)
        self.service.completed.connect(self.on_completed)
        self._busy = False
        self._watching = 0
        self._quitting = False
        self._closed = False
        self._shutdown_state = 'running'
        self._setup_pending = False
        self.selected_path = self.settings.folders[0].path if self.settings.folders else ""
        self.setWindowTitle("FileFlow")
        self.setWindowIcon(brand_icon())
        self.resize(1180, 850)
        self.setMinimumSize(820, 600)
        self.tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_icon.activated.connect(self.tray_activated)
        self.build()
        self.service.start()
        self.service.configure(self.settings.folders, self.settings.automatic)
        if self.load_error:
            QTimer.singleShot(0, lambda: QMessageBox.warning(self, "FileFlow", self.t("settings_error", path=self.store.path, error=self.load_error)))

    def t(self, key, **values):
        locale = QLocale('ar_SA' if self.settings.language == 'ar' else 'en_GB')
        values = {k: locale.toString(v) if isinstance(v, int) and not isinstance(v, bool) else v for k, v in values.items()}
        return tr(key, self.settings.language, **values)

    def persist(self):
        if self.load_error and not any(f.confirmed for f in self.settings.folders):
            return False
        try:
            if self.load_error:
                # Recovery is allowed only after the user confirms a new setup.
                import shutil
                from datetime import datetime
                backup = self.store.path.with_name("settings.corrupt-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
                shutil.copy2(self.store.path, backup)
                self.load_error = ""
            self.store.save(self.settings)
            return True
        except OSError as error:
            self.toast.notify(self.t("save_error", error=error), True)
            return False

    def commit(self, proposed: Settings):
        previous = self.settings
        self.settings = proposed
        if not self.persist():
            self.settings = previous
            return False
        self.service.configure(self.settings.folders, self.settings.automatic)
        return True

    def current_folder(self):
        return next((f for f in self.settings.folders if f.path == self.selected_path), None)

    def select_folder(self, current, previous):
        if current:
            self.selected_path = current.data(Qt.ItemDataRole.UserRole)
            self.render_folder()

    def choose_folder(self):
        if self._setup_pending:
            return
        path = QFileDialog.getExistingDirectory(self, self.t("choose"))
        if path:
            self.setup_folder(path)

    def setup_folder(self, path):
        try:
            root = validate_root(path)
            if root == self.store.path.parent.absolute().resolve():
                raise ValueError("protected_settings")
            for folder in self.settings.folders:
                other = Path(folder.path)
                if root == other or root in other.parents or other in root.parents:
                    raise ValueError("overlap")
        except (OSError, ValueError):
            self.toast.notify(self.t("folder_error"), True)
            return False
        # Pause first: a folder picker/setup must never activate existing automation.
        self._setup_pending = True
        self.service.configure(self.settings.folders, False)
        confirm = QMessageBox(self)
        confirm.setWindowTitle(self.t("setup_title"))
        confirm.setText(self.t("setup_body", path=root))
        accept = confirm.addButton(self.t("confirm"), QMessageBox.ButtonRole.AcceptRole)
        cancel_button = confirm.addButton(self.t("cancel"), QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(cancel_button)
        confirm.setEscapeButton(cancel_button)
        confirm.exec()
        self._setup_pending = False
        if confirm.clickedButton() != accept:
            self.service.configure(self.settings.folders, self.settings.automatic)
            return False
        proposed = deepcopy(self.settings)
        proposed.folders.append(Folder(str(root), confirmed=True))
        # Adding a folder always returns to manual, so existing contents never move implicitly.
        proposed.automatic = False
        if self.commit(proposed):
            self.selected_path = str(root)
            self.build()
            self.toast.notify(self.t("folder_added"))
            return True
        self.service.configure(self.settings.folders, self.settings.automatic)
        return False

    def remove_folder(self):
        proposed = deepcopy(self.settings)
        proposed.folders = [f for f in proposed.folders if f.path != self.selected_path]
        if not proposed.folders:
            proposed.automatic = False
        if self.commit(proposed):
            self.selected_path = proposed.folders[0].path if proposed.folders else ""
            self.build()

    def edit_destination(self, category):
        folder = self.current_folder()
        dialog = EditDialog(self, folder.destinations[category])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proposed = deepcopy(self.settings)
            next(f for f in proposed.folders if f.path == folder.path).destinations[category] = dialog.result_destination
            if self.commit(proposed):
                self.render_folder()

    def add_rule(self):
        dialog = EditDialog(self, "Documents", Rule())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proposed = deepcopy(self.settings)
            next(f for f in proposed.folders if f.path == self.selected_path).rules.append(dialog.result_rule)
            if self.commit(proposed):
                self.render_folder()
                self.apply_theme()
                self.toast.notify(self.t("rule_saved"))

    def enable_rule(self, id, enabled):
        proposed = deepcopy(self.settings)
        folder = next(f for f in proposed.folders if f.path == self.selected_path)
        next(r for r in folder.rules if r.id == id).enabled = enabled
        if not self.commit(proposed):
            self.render_folder()
        elif hasattr(self, 'rule_controls') and id in self.rule_controls:
            control = self.rule_controls[id]
            control.setText(self.t('enabled' if enabled else 'disabled'))
            card = control.parentWidget()
            card.setProperty('enabledRule', enabled)
            card.style().unpolish(card); card.style().polish(card)

    def remove_rule(self, id):
        proposed = deepcopy(self.settings)
        folder = next(f for f in proposed.folders if f.path == self.selected_path)
        folder.rules = [r for r in folder.rules if r.id != id]
        if self.commit(proposed):
            self.render_folder()

    def toggle_auto(self, enabled):
        self._monitor_notice = True
        self.monitor_label.setText(self.t("updating_monitor"))
        proposed = deepcopy(self.settings)
        proposed.automatic = enabled
        if not self.commit(proposed):
            self.auto.blockSignals(True)
            self.auto.setChecked(self.settings.automatic)
            self.auto.blockSignals(False)
            self._monitor_notice = False
            self.monitor_label.setText(self.t("watching", n=self._watching) if self._watching else self.t("off"))

    def preference(self, key, value):
        previous = getattr(self.settings, key)
        setattr(self.settings, key, value)
        if not self.persist():
            setattr(self.settings, key, previous)
            return False
        return True

    def change_language(self):
        if self._quitting: return
        started = time.perf_counter()
        if self.preference('language', 'en' if self.settings.language == 'ar' else 'ar'):
            self.retranslate()
        diagnostic('language_switched', elapsed_ms=round((time.perf_counter()-started)*1000,3), language=self.settings.language)

    def change_theme(self):
        if self._quitting: return
        started = time.perf_counter()
        if self.preference('theme', 'dark' if self.settings.theme == 'light' else 'light'):
            self.setUpdatesEnabled(False)
            try:
                self.apply_theme()
                self.update_preference_captions()
            finally: self.setUpdatesEnabled(True); self.update()
        diagnostic('theme_switched', elapsed_ms=round((time.perf_counter()-started)*1000,3), theme=self.settings.theme)

    def set_tray(self, enabled):
        if self.preference('tray', enabled):
            self.tray_icon.setVisible(enabled and QSystemTrayIcon.isSystemTrayAvailable())
        else:
            self.tray_check.blockSignals(True)
            self.tray_check.setChecked(self.settings.tray)
            self.tray_check.blockSignals(False)

    def on_activity(self, activity: Activity):
        self.settings.history.append(activity.to_dict())
        self.settings.history = self.settings.history[-200:]
        if self._quitting:
            return  # Keep final successful moves, but do not recreate UI during teardown.
        if getattr(self, '_background', False):
            self._history_dirty = True
            return
        if not hasattr(self, 'activity_timer'):
            self.activity_timer = QTimer(self)
            self.activity_timer.setSingleShot(True)
            self.activity_timer.setInterval(120)
            self.activity_timer.timeout.connect(self.render_history)
        if not self.activity_timer.isActive():
            self.activity_timer.start()
        # Persist at scan completion; batch table refreshes during large moves.

    def restore(self):
        self._background = False
        scroll = self.history_table.verticalScrollBar().value()
        card = getattr(self.history_table, 'card', None)
        expanded = card.expand_button.isChecked() if card else None
        if getattr(self, '_history_dirty', False):
            self._history_dirty = False
            self.render_history()
            card = getattr(self.history_table, 'card', None)
            if card and expanded is not None:
                card.expand_button.setChecked(expanded)
                card.reveal_animation.setCurrentTime(card.reveal_animation.duration())
            self.history_table.verticalScrollBar().setValue(scroll)
            self._restore_generation = getattr(self, '_restore_generation', 0) + 1
            generation = self._restore_generation
            def restore_scroll():
                if not self._quitting and generation == self._restore_generation:
                    self.history_table.verticalScrollBar().setValue(scroll)
            QTimer.singleShot(0, restore_scroll)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._quitting: return
        self._background = True
        if hasattr(self, 'toast'):
            self.toast.timer.stop()
            self.toast.hide()
        for animation in self.findChildren(QAbstractAnimation): animation.stop()
        for name in ('activity_timer', 'search_timer'):
            timer = getattr(self, name, None)
            if timer and timer.isActive():
                timer.stop(); self._history_dirty = True

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore()

    def quit_app(self):
        self._quitting = True
        self.begin_shutdown()

    def begin_shutdown(self):
        if self._shutdown_state != 'running': return
        self._quitting = True
        self._shutdown_state = 'draining'
        self._shutdown_start = time.monotonic()
        diagnostic('shutdown_requested')
        self.centralWidget().setEnabled(False)
        for timer in self.findChildren(QTimer): timer.stop()
        for animation in self.findChildren(QAbstractAnimation): animation.stop()
        self.service.request_shutdown()
        self._shutdown_poll = QTimer(self)
        self._shutdown_poll.setInterval(20)
        self._shutdown_poll.timeout.connect(self.poll_shutdown)
        self._shutdown_poll.start()
        self.poll_shutdown()

    def poll_shutdown(self):
        if self._shutdown_state != 'draining': return
        if not self.service.is_finished():
            elapsed = time.monotonic() - self._shutdown_start
            if elapsed > 5 and not getattr(self, '_shutdown_warning', False):
                self._shutdown_warning = True
                diagnostic('shutdown_waiting', elapsed_ms=round(elapsed * 1000, 2))
                self.tray_icon.setToolTip(self.t('shutdown_waiting'))
                self.toast.notify(self.t('shutdown_waiting'), True)
                self.show()
            return
        self._shutdown_poll.stop()
        # Drain queued final Activity events before persisting and invalidating callbacks.
        QCoreApplication.sendPostedEvents(self, QEvent.Type.MetaCall)
        self.service.shutdown(timeout=0)
        self.persist()
        for timer in self.findChildren(QTimer): timer.stop()
        for animation in self.findChildren(QAbstractAnimation): animation.stop()
        for name in ('activity', 'busy', 'monitoring', 'watched_paths', 'completed'):
            getattr(self.service, name).disconnect()
        self.tray_icon.hide()
        self.tray_icon.deleteLater()
        self._shutdown_state = 'complete'
        self._closed = True
        diagnostic('shutdown_complete', elapsed_ms=round((time.monotonic() - self._shutdown_start) * 1000, 2))
        self.close()
        self.shutdown_finished.emit()

    def closeEvent(self, event):
        if self._shutdown_state == 'complete':
            event.accept()
            return
        if self.settings.tray and QSystemTrayIcon.isSystemTrayAvailable() and not self._quitting:
            self.hide()
            event.ignore()
            return
        self.begin_shutdown()
        event.ignore()
