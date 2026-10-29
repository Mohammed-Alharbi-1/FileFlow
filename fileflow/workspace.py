"""Presentation layer for the existing MainWindow controller and organizer service."""
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QStackedWidget, QListWidget, QListWidgetItem, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMenu,
    QSystemTrayIcon, QGraphicsOpacityEffect, QSizePolicy, QGridLayout)
from .controls import HoverButton, CheckBox, Switch, Toast, Card, motion_duration
from .models import CATEGORIES
from .refinement import Refinement
from .visuals import vector_icon, StatusPill, FilterCombo
from .localization import bind, role


def make_button(text, callback, name=''):
    result = HoverButton(text)
    result.setObjectName(name)
    result.clicked.connect(callback)
    return bind(result, text, role(callback))


class Workspace(Refinement):
    sections = ('dashboard', 'folders', 'rules', 'history', 'settings')

    def build(self):
        from .ui import label, brand_icon
        self._section = getattr(self, '_section', 'dashboard')
        self._filter_folder = getattr(self, '_filter_folder', '')
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.settings.language == 'ar' else Qt.LayoutDirection.LeftToRight)
        old = self.takeCentralWidget()
        if old:
            self._history_query = self.search.text()
            self._history_status = self.status_filter.currentData()
            self._history_date = self.date_filter.currentData()
            old.deleteLater()
        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        side = QFrame()
        side.setObjectName('sidebar')
        side.setFixedWidth(202)
        nav = QVBoxLayout(side)
        nav.setContentsMargins(18, 28, 18, 20)
        nav.setSpacing(8)
        branding = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(brand_icon().pixmap(30, 30))
        branding.addWidget(icon)
        branding.addWidget(label('FileFlow', 'brand'), 1)
        nav.addLayout(branding)
        nav.addSpacing(25)
        self.nav_buttons = {}
        for key in self.sections:
            action = make_button(self.t('nav_' + key) if key in ('history', 'rules') else self.t(key), lambda checked=False, name=key: self.navigate(name), 'navigation')
            action.setIcon(vector_icon(key))
            action.setIconSize(QSize(18, 18))
            action.setCheckable(True)
            self.nav_buttons[key] = action
            nav.addWidget(action)
        nav.addSpacing(22)
        nav.addWidget(label(self.t('folders'), 'eyebrow'))
        self.folder_list = QListWidget()
        self.folder_list.setObjectName('folderList')
        for folder in self.settings.folders:
            item = QListWidgetItem(Path(folder.path).name or folder.path)
            item.setData(Qt.ItemDataRole.UserRole, folder.path)
            item.setToolTip(folder.path)
            self.folder_list.addItem(item)
            if folder.path == self.selected_path:
                self.folder_list.setCurrentItem(item)
        self.folder_list.currentItemChanged.connect(self.select_folder)
        nav.addWidget(self.folder_list, 1)
        self.add_folder_button = make_button('+  ' + self.t('choose'), self.choose_folder)
        nav.addWidget(self.add_folder_button)
        nav.addWidget(label(self.t('local_note'), 'micro', True))
        shell.addWidget(side)
        main = QVBoxLayout()
        main.setContentsMargins(26, 22, 26, 16)
        main.setSpacing(14)
        top = QHBoxLayout()
        self.page_title = label('', 'hero')
        top.addWidget(self.page_title, 1)
        self.language = make_button('English' if self.settings.language == 'ar' else 'العربية', self.change_language, 'quiet')
        top.addWidget(self.language)
        top.addWidget(make_button(self.t('dark' if self.settings.theme == 'light' else 'light'), self.change_theme, 'quiet'))
        main.addLayout(top)
        self.stack = QStackedWidget()
        self.pages = {}
        self.page_layouts = {}
        self.scrolls = {}
        for key in self.sections:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(14)
            self.pages[key], self.page_layouts[key] = page, layout
            if key == 'history':
                self.stack.addWidget(page)
            else:
                scroll = QScrollArea()
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setWidget(page)
                self.scrolls[key] = scroll
                self.stack.addWidget(scroll)
        main.addWidget(self.stack, 1)
        shell.addLayout(main, 1)
        dashboard = self.page_layouts['dashboard']
        dashboard.addWidget(label(self.t('workspace'), 'section'))
        control, row = self.panel()
        auto_copy = QVBoxLayout()
        self.auto = bind(Switch(self.t('auto')), self.t('auto'))
        self.auto.setChecked(self.settings.automatic)
        self.auto.setEnabled(bool(self.settings.folders))
        self.auto.toggled.connect(self.toggle_auto)
        auto_copy.addWidget(self.auto)
        auto_copy.addWidget(label(self.t('auto_hint'), 'micro', True))
        self.monitor_label = StatusPill(self.t('watching', n=self._watching) if self._watching else self.t('off'), 'success' if self._watching else 'neutral')
        self.state_label = self.monitor_label
        auto_copy.addWidget(self.monitor_label)
        auto_host = QWidget()
        auto_host.setLayout(auto_copy)
        auto_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(auto_host, 1)
        self.organize_button = make_button(self.t('working' if self._busy else 'organize'), self.start_organization, 'primary')
        self.organize_button.setEnabled(bool(self.settings.folders) and not self._busy)
        self.organize_button.setFixedWidth(164)
        self.organize_button.setToolTip(self.t('all_folders'))
        row.addWidget(self.organize_button)
        dashboard.addWidget(control)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setVisible(self._busy)
        dashboard.addWidget(self.progress)
        self.detail = QWidget()
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(9)
        dashboard.addWidget(self.detail)
        recent_panel = Card()
        recent_panel.setObjectName('recentPanel')
        recent_body = QVBoxLayout(recent_panel)
        recent_body.setContentsMargins(16, 12, 16, 12)
        recent_head = QHBoxLayout()
        recent_head.addWidget(label(self.t('history'), 'section'), 1)
        recent_head.addWidget(make_button(self.t('view_all'), lambda: self.navigate('history'), 'quiet'))
        recent_body.addLayout(recent_head)
        recent_host = QWidget()
        self.recent_layout = QVBoxLayout(recent_host)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(0)
        recent_body.addWidget(recent_host)
        dashboard.addWidget(recent_panel)
        dashboard.addStretch()
        self.folder_cards = QWidget()
        self.folder_cards_layout = QVBoxLayout(self.folder_cards)
        self.folder_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.page_layouts['folders'].addWidget(self.folder_cards)
        self.page_layouts['folders'].addStretch()
        rules_head = QHBoxLayout()
        self.rule_folder = FilterCombo()
        self.rule_folder.setAccessibleName(self.t('folders'))
        for folder in self.settings.folders:
            self.rule_folder.addItem(Path(folder.path).name or folder.path, folder.path)
        self.rule_folder.setCurrentIndex(self.rule_folder.findData(self.selected_path))
        self.rule_folder.currentIndexChanged.connect(self.rule_folder_changed)
        rules_head.addWidget(self.rule_folder, 1)
        self.add_rule_button = make_button('+  ' + self.t('add_rule'), self.add_rule)
        self.add_rule_button.setEnabled(bool(self.settings.folders))
        rules_head.addWidget(self.add_rule_button)
        self.page_layouts['rules'].addLayout(rules_head)
        self.page_layouts['rules'].addWidget(label(self.t('rules_hint'), 'muted', True))
        self.rule_rows = QWidget()
        self.rule_rows_layout = QVBoxLayout(self.rule_rows)
        self.rule_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.page_layouts['rules'].addWidget(self.rule_rows)
        self.page_layouts['rules'].addStretch()
        self.build_history()
        preferences = self.page_layouts['settings']
        preferences.addWidget(label(self.t('appearance'), 'section'))
        preferences.addWidget(make_button(self.t('dark' if self.settings.theme == 'light' else 'light'), self.change_theme))
        preferences.addWidget(make_button('English / العربية', self.change_language))
        self.tray_check = bind(Switch(self.t('tray')), self.t('tray'))
        self.tray_check.setChecked(self.settings.tray)
        self.tray_check.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        self.tray_check.setToolTip(self.t('tray_description'))
        self.tray_check.toggled.connect(self.set_tray)
        preferences.addWidget(self.tray_check)
        preferences.addWidget(label(self.t('tray_description'), 'muted', True))
        preferences.addWidget(label(self.t('startup_hint'), 'micro', True))
        preferences.addWidget(label(self.t('safety'), 'muted', True))
        preferences.addStretch()
        self.toast = Toast(central)
        menu = QMenu(self)
        bind(menu.addAction(self.t('show'), self.restore), self.t('show'))
        bind(menu.addAction(self.t('quit'), self.quit_app), self.t('quit'))
        previous_menu = self.tray_icon.contextMenu()
        self.tray_icon.setContextMenu(menu)
        if previous_menu:
            previous_menu.deleteLater()
        self.tray_icon.setToolTip('FileFlow')
        self.tray_icon.setVisible(self.settings.tray and QSystemTrayIcon.isSystemTrayAvailable())
        self.render_folder()
        self.render_history()
        self.apply_theme()
        self.navigate(self._section, animate=False)

    def panel(self):
        panel = Card()
        panel.setObjectName('panel')
        row = QHBoxLayout(panel)
        row.setContentsMargins(16, 12, 16, 12)
        return panel, row

    def navigate(self, section, animate=True):
        self._section = section
        self.stack.setCurrentIndex(self.sections.index(section))
        self.page_title.setText(self.t('nav_' + section) if section in ('history', 'rules') else self.t(section))
        for name, button in self.nav_buttons.items():
            button.setChecked(name == section)
        if not hasattr(self, '_page_effect') or self._page_effect.parent() != self.stack:
            self._page_effect = QGraphicsOpacityEffect(self.stack)
            self.stack.setGraphicsEffect(self._page_effect)
            self._transition = QPropertyAnimation(self._page_effect, b'opacity', self.stack)
            self._transition.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._transition.stop()
        self._transition.setDuration(motion_duration() if animate else 0)
        self._transition.setStartValue(.5 if animate else 1.0)
        self._transition.setEndValue(1.0)
        self._transition.start()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def choose_existing(self, path):
        self.selected_path = path
        for row in range(self.folder_list.count()):
            if self.folder_list.item(row).data(Qt.ItemDataRole.UserRole) == path:
                self.folder_list.setCurrentRow(row)
        self.render_folder()

    def rule_folder_changed(self, index):
        path = self.rule_folder.itemData(index)
        if path:
            self.choose_existing(path)

    def folder_rules(self, path):
        self.choose_existing(path)
        self.navigate('rules')

    def folder_history(self, path):
        self._filter_folder = path
        index = self.history_folder.findData(path)
        if index < 0:
            self.history_folder.addItem(Path(path).name or path, path)
            index = self.history_folder.count() - 1
        self.history_folder.setCurrentIndex(index)
        self.render_history()
        self.navigate('history')

    def open_event(self, event):
        if event and event['status'] == 'success' and event['destination']:
            self.open_folder_path(str(Path(event['destination']).parent))

    def open_selected(self):
        self.open_event(self.selected_event())

    def open_folder_path(self, path):
        try:
            if not Path(path).is_dir() or not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                raise OSError(self.t('missing'))
        except OSError:
            self.state_label.setText(self.t('missing'))
            self.toast.notify(self.t('missing'), True)

    def start_organization(self):
        if self._quitting or self._busy or not self.settings.folders:
            return
        self.on_busy(True)
        self.service.organize_now()

    def on_busy(self, busy):
        if self._quitting: return
        self._busy = busy
        self.organize_button.setText(self.t('working' if busy else 'organize'))
        self.organize_button.setEnabled(not busy and bool(self.settings.folders))
        self.progress.setVisible(busy)

    def on_monitoring(self, count):
        if self._quitting: return
        self._watching = count
        text = self.t('watching', n=count) if count else self.t('off')
        if self.settings.automatic and count < len(self.settings.folders):
            text = self.t('monitor_failed')
        self.state_label.setText(text)
        self.monitor_label.setText(text)
        self.monitor_label.setTone('success' if count else 'neutral')
        if getattr(self, '_monitor_notice', False):
            self.toast.notify(text, self.settings.automatic and count < len(self.settings.folders))
            self._monitor_notice = False

    def on_watched_paths(self, paths):
        if self._quitting: return
        self._watched_paths = set(paths)
        self.render_folder_cards()

    def on_completed(self, moved, errors, manual):
        if self._quitting: return
        if manual or moved or errors:
            text = self.t('done', n=moved, e=errors)
            self.persist()
            if not getattr(self, '_background', False): self.toast.notify(text, bool(errors))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'toast'):
            self.toast.anchor()

