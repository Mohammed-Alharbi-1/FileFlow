"""FileFlow 1.2 page components, separate from the existing application controller."""
from datetime import datetime, timedelta
from pathlib import Path
from copy import deepcopy
from PySide6.QtCore import Qt, QTimer, QSize, QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget, QFrame, QLabel, QLineEdit, QComboBox, QVBoxLayout, QHBoxLayout, QGridLayout, QMenu, QListWidgetItem, QDialog, QSizePolicy
from .controls import HoverButton, Switch, Card
from .visuals import vector_icon, badge, COLORS, path_field, timestamp, ElideLabel, StatusPill, ActivityList, ActivityCard, category_for, FilterCombo
from .models import CATEGORIES
from .localization import bind, bind_key, role
from .history_view import HistoryView


def action(text, callback, name='quiet', icon=None):
    result = HoverButton(text); result.setObjectName(name); result.clicked.connect(callback)
    if icon: result.setIcon(vector_icon(icon))
    return bind(result, text, role(callback)) if name != 'folderTitle' else result


def text(value, name='muted', wrap=False):
    result = QLabel(value); result.setObjectName(name); result.setTextFormat(Qt.TextFormat.PlainText); result.setWordWrap(wrap)
    return bind(result, value)


class Refinement:
    def update_preference_captions(self):
        for obj in self.findChildren(QObject):
            target = obj.property('ffRole')
            if target == 'theme': obj.setText(self.t('light' if self.settings.theme == 'dark' else 'dark'))
            elif target == 'language': obj.setText('English' if self.settings.language == 'ar' else 'العربية')

    def retranslate(self):
        """Translate in place; keep cards, editors, connections, selection and scrolls."""
        scrolls = [scroll.verticalScrollBar() for scroll in self.scrolls.values()] + [self.history_table.verticalScrollBar()]
        positions = [(bar, bar.value()) for bar in scrolls]
        self.setUpdatesEnabled(False)
        try:
            rtl = self.settings.language == 'ar'
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
            for obj in self.findChildren(QObject):
                key = obj.property('ffTextKey')
                if key and hasattr(obj, 'setText'):
                    value = self.t(key, **(obj.property('ffTextValues') or {}))
                    if isinstance(obj, ElideLabel): obj.full_text = value
                    obj.setText(value)
                title = obj.property('ffTitleKey')
                if title: obj.setWindowTitle(self.t(title))
                stamp = obj.property('ffTimestamp')
                if stamp:
                    obj.setText(timestamp(stamp, self.settings.language))
                    obj.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
                if obj.property('ffFileName'):
                    obj.setAlignment(Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)
            self.page_title.setText(self.t('nav_' + self._section) if self._section in ('rules','history') else self.t(self._section))
            self.update_preference_captions()
            self.add_folder_button.setText('+  ' + self.t('choose'))
            self.organize_button.setToolTip(self.t('all_folders'))
            self.tray_check.setToolTip(self.t('tray_description'))
            self.history_folder.setAccessibleName(self.t('folders'))
            self.status_filter.setAccessibleName(self.t('status'))
            self.date_filter.setAccessibleName(self.t('date'))
            self.search.setPlaceholderText(self.t('search_files')); self.search.setAccessibleName(self.t('search_files'))
            for box in (self.history_folder, self.status_filter, self.date_filter):
                box.blockSignals(True)
                for index in range(box.count()):
                    key = box.itemData(index)
                    if box is self.history_folder and not key: box.setItemText(index, self.t('all_folders_filter'))
                    elif box is self.status_filter: box.setItemText(index, self.t(key or 'all_statuses'))
                    elif box is self.date_filter: box.setItemText(index, self.t(key))
                box.blockSignals(False)
            for box in self.findChildren(FilterCombo):
                if box.count() == 2 and box.itemData(0) == 'extension':
                    box.setItemText(0, self.t('extension')); box.setItemText(1, self.t('contains'))
            for control in self.rule_controls.values():
                control.setText(self.t('enabled' if control.isChecked() else 'disabled'))
            for card in self.activity_cards: card.refresh_locale()
            self.history_summary.setText(self.t('history_count', n=len(self._history_rows), total=len(self.settings.history)))
            self.organize_button.setText(self.t('working' if self._busy else 'organize'))
            monitor = self.t('updating_monitor') if getattr(self, '_monitor_notice', False) else self.t('watching', n=self._watching) if self._watching else self.t('off')
            if self.settings.automatic and not getattr(self, '_monitor_notice', False) and self._watching < len(self.settings.folders): monitor = self.t('monitor_failed')
            self.monitor_label.setText(monitor)
        finally: self.setUpdatesEnabled(True); self.update()
        for bar, value in positions: bar.setValue(value)
        self._locale_generation = getattr(self, '_locale_generation', 0) + 1
        generation = self._locale_generation
        def restore():
            if not self._quitting and generation == self._locale_generation:
                for bar, value in positions: bar.setValue(value)
        QTimer.singleShot(0, restore)

    def render_folder(self):
        self.clear_layout(self.detail_layout); self.clear_layout(self.rule_rows_layout)
        self.rule_controls = {}
        folder = self.current_folder()
        if folder:
            heading = QHBoxLayout(); heading.addWidget(text(self.t('categories'), 'section')); heading.addStretch()
            caption = ElideLabel(Path(folder.path).name or folder.path, 'folderCaption'); caption.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred); caption.setFixedWidth(160); heading.addWidget(caption)
            head = QWidget(); head.setLayout(heading); self.detail_layout.addWidget(head)
            grid_widget = QWidget(); grid = QGridLayout(grid_widget); grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(10)
            grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
            for index, (category, extensions) in enumerate(CATEGORIES.items()):
                card = Card(); card.setObjectName('categoryCard')
                body = QVBoxLayout(card); body.setContentsMargins(13, 10, 13, 10); body.setSpacing(7)
                row = QHBoxLayout(); row.setSpacing(10); row.addWidget(badge(category))
                copy = QVBoxLayout(); copy.setSpacing(1); copy.addWidget(text(self.t(category), 'cardTitle'))
                description = ElideLabel(' · '.join(extensions) if extensions else self.t('other_hint'), 'micro')
                if not extensions: bind_key(description, 'other_hint')
                copy.addWidget(description); row.addLayout(copy, 1)
                edit = action('', lambda checked=False, key=category: self.edit_destination(key), 'iconButton', 'edit')
                edit.setFixedSize(34, 34); edit.setAccessibleName(self.t('edit') + ': ' + self.t(category)); edit.setToolTip(edit.accessibleName())
                row.addWidget(edit); body.addLayout(row)
                if index < 6:
                    route = QHBoxLayout(); route.setSpacing(6); route.addWidget(text(self.t('destination'), 'micro'))
                    destination = ElideLabel(folder.destinations[category], 'route'); destination.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    route.addWidget(destination, 1); body.addLayout(route)
                    grid.addWidget(card, index // 2, index % 2)
                else:
                    edit.setToolTip(self.t('edit') + ': ' + folder.destinations[category])
                    grid.addWidget(card, 3, 0, 1, 2)
            self.detail_layout.addWidget(grid_widget)
            for index, rule in enumerate(folder.rules):
                card = Card(); card.setObjectName('ruleCard'); card.setProperty('enabledRule', rule.enabled)
                body = QVBoxLayout(card); body.setContentsMargins(18, 15, 18, 15); body.setSpacing(10)
                header = QHBoxLayout(); header.addWidget(badge('rules'))
                condition = QVBoxLayout(); condition.setSpacing(2)
                condition.addWidget(text(self.t(rule.kind), 'eyebrow'))
                match_value = ElideLabel(rule.value, 'ruleValue'); match_value.setAlignment(Qt.AlignmentFlag.AlignRight if self.settings.language == 'ar' else Qt.AlignmentFlag.AlignLeft)
                condition.addWidget(match_value); header.addLayout(condition, 1)
                switch = Switch(self.t('enabled') if rule.enabled else self.t('disabled'))
                switch.setChecked(rule.enabled); switch.setProperty('dark', self.settings.theme == 'dark')
                switch.setAccessibleName(self.t('enabled') + ': ' + rule.value)
                switch.setFixedWidth(120)
                switch.toggled.connect(lambda value, id=rule.id: self.enable_rule(id, value))
                self.rule_controls[rule.id] = switch; header.addWidget(switch); body.addLayout(header)
                body.addWidget(text(self.t('destination'), 'eyebrow')); body.addWidget(path_field(rule.destination))
                toolbar = QHBoxLayout(); toolbar.addWidget(bind_key(text(self.t('priority', n=index + 1), 'micro'), 'priority', n=index + 1)); toolbar.addStretch()
                toolbar.addWidget(action(self.t('edit_rule'), lambda checked=False, id=rule.id: self.edit_rule(id), 'quiet', 'edit'))
                toolbar.addWidget(action(self.t('delete'), lambda checked=False, id=rule.id: self.remove_rule(id), 'danger'))
                body.addLayout(toolbar); self.rule_rows_layout.addWidget(card)
            if not folder.rules:
                self.rule_rows_layout.addWidget(self.empty_state('rules', self.t('no_rules')))
        else:
            self.detail_layout.addWidget(self.empty_state('folder', self.t('empty_body')))
            self.rule_rows_layout.addWidget(self.empty_state('rules', self.t('empty_body')))
        self.rule_folder.blockSignals(True); self.rule_folder.setCurrentIndex(self.rule_folder.findData(self.selected_path)); self.rule_folder.blockSignals(False)
        self.render_folder_cards()

    def empty_state(self, icon, message):
        panel = Card(); panel.setObjectName('emptyState'); body = QVBoxLayout(panel); body.setContentsMargins(24, 24, 24, 24); body.setSpacing(12)
        body.addWidget(badge(icon, size=42), 0, Qt.AlignmentFlag.AlignHCenter)
        caption = text(message, 'muted', True); caption.setAlignment(Qt.AlignmentFlag.AlignCenter); body.addWidget(caption)
        return panel

    def edit_rule(self, id):
        from .ui import EditDialog
        folder = self.current_folder(); rule = next(r for r in folder.rules if r.id == id)
        dialog = EditDialog(self, rule.destination, rule)
        dialog.setWindowTitle(self.t('edit_rule'))
        dialog.setProperty('ffTitleKey', 'edit_rule')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proposed = deepcopy(self.settings)
            target = next(f for f in proposed.folders if f.path == folder.path)
            index = next(i for i, candidate in enumerate(target.rules) if candidate.id == id)
            replacement = dialog.result_rule; replacement.id = rule.id; replacement.enabled = rule.enabled
            target.rules[index] = replacement
            if self.commit(proposed):
                self.render_folder(); self.toast.notify(self.t('rule_saved'))

    def render_folder_cards(self):
        self.clear_layout(self.folder_cards_layout)
        for entry in self.settings.folders:
            card = Card(); card.setObjectName('folderCard'); card.setProperty('selected', entry.path == self.selected_path)
            body = QVBoxLayout(card); body.setContentsMargins(18, 14, 18, 12); body.setSpacing(10)
            header = QHBoxLayout(); header.setSpacing(10); header.addWidget(badge('folder', '#688ddd', 38))
            title = action(Path(entry.path).name or entry.path, lambda checked=False, path=entry.path: self.choose_existing(path), 'folderTitle')
            title.setText(title.fontMetrics().elidedText(title.text(), Qt.TextElideMode.ElideMiddle, 300)); title.setToolTip(entry.path)
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed); header.addWidget(title, 1)
            active = entry.path in getattr(self, '_watched_paths', set())
            header.addWidget(StatusPill(self.t('watching_short') if active else self.t('off'), 'success' if active else 'neutral'))
            body.addLayout(header)
            field = path_field(entry.path); field.setAccessibleName(self.t('source')); body.addWidget(field)
            toolbar = QHBoxLayout(); toolbar.setSpacing(4)
            toolbar.addWidget(action(self.t('nav_rules'), lambda checked=False, path=entry.path: self.folder_rules(path), 'quiet', 'rules'))
            toolbar.addWidget(action(self.t('nav_history'), lambda checked=False, path=entry.path: self.folder_history(path), 'quiet', 'history'))
            toolbar.addWidget(action(self.t('open'), lambda checked=False, path=entry.path: self.open_folder_path(path), 'quiet', 'open'))
            toolbar.addStretch(); toolbar.addWidget(bind_key(text(self.t('rule_count', n=len(entry.rules)), 'micro'), 'rule_count', n=len(entry.rules)))
            more = HoverButton(''); more.setIcon(vector_icon('more')); more.setObjectName('iconButton'); more.setFixedWidth(36)
            more.setAccessibleName(self.t('folder_actions')); more.setToolTip(self.t('folder_actions'))
            menu = QMenu(more); bind(menu.addAction(self.t('remove_folder'), lambda path=entry.path: self.remove_folder_path(path)), self.t('remove_folder'))
            more.setMenu(menu); toolbar.addWidget(more); body.addLayout(toolbar)
            self.folder_cards_layout.addWidget(card)
        if not self.settings.folders:
            self.folder_cards_layout.addWidget(self.empty_state('folder', self.t('empty_body')))

    def remove_folder_path(self, path):
        self.selected_path = path
        self.remove_folder()

    def build_history(self):
        layout = self.page_layouts['history']
        filters_panel = QFrame(); filters_panel.setObjectName('filterBar'); filters = QGridLayout(filters_panel); filters.setContentsMargins(0, 0, 0, 0); filters.setSpacing(8)
        self.search = QLineEdit(getattr(self, '_history_query', '')); self.search.setPlaceholderText(self.t('search_files')); self.search.setAccessibleName(self.t('search_files'))
        self.search.addAction(vector_icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self.history_folder = FilterCombo(); self.history_folder.setAccessibleName(self.t('folders')); self.history_folder.addItem(self.t('all_folders_filter'), '')
        paths = dict.fromkeys([f.path for f in self.settings.folders] + [str(Path(h['source']).parent) for h in self.settings.history if h['source']])
        for path in paths:
            self.history_folder.addItem(Path(path).name or path, path); self.history_folder.setItemData(self.history_folder.count() - 1, path, Qt.ItemDataRole.ToolTipRole)
        self.history_folder.setCurrentIndex(max(0, self.history_folder.findData(self._filter_folder)))
        self.status_filter = FilterCombo(); self.status_filter.setAccessibleName(self.t('status'))
        for key, caption in (('', 'all_statuses'), ('success', 'success'), ('error', 'error'), ('deferred', 'deferred')): self.status_filter.addItem(self.t(caption), key)
        self.date_filter = FilterCombo(); self.date_filter.setAccessibleName(self.t('date'))
        for key in ('all_dates', 'today', 'week'): self.date_filter.addItem(self.t(key), key)
        self.status_filter.setCurrentIndex(max(0, self.status_filter.findData(getattr(self, '_history_status', ''))))
        self.date_filter.setCurrentIndex(max(0, self.date_filter.findData(getattr(self, '_history_date', 'all_dates'))))
        filters.addWidget(self.search, 0, 0, 1, 3)
        for column, box in enumerate((self.history_folder, self.status_filter, self.date_filter)):
            box.setMinimumWidth(0); box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed); filters.addWidget(box, 1, column); filters.setColumnStretch(column, 1)
        layout.addWidget(filters_panel)
        self.history_summary = text('', 'micro'); layout.addWidget(self.history_summary)
        self.history_table = HistoryView(self); self.history_table.setObjectName('activityList'); self.history_table.setSpacing(5)
        self.history_table.setSelectionMode(ActivityList.SelectionMode.SingleSelection)
        self.history_table.setVerticalScrollMode(ActivityList.ScrollMode.ScrollPerPixel)
        self.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_table.itemSelectionChanged.connect(self.history_selection)
        self.history_table.itemDoubleClicked.connect(lambda *_: self.open_selected())
        layout.addWidget(self.history_table, 1)
        self.history_empty = self.empty_state('history', self.t('history_empty')); layout.addWidget(self.history_empty)
        self.history_empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.empty_spacer = QWidget(); self.empty_spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.empty_spacer, 1)
        self.history_details = text(self.t('select_activity'))
        self.open_button = action(self.t('open'), self.open_selected, 'quiet', 'open'); self.open_button.setEnabled(False)
        footer = QHBoxLayout(); footer.addWidget(text(self.t('select_activity'), 'micro'), 1); footer.addWidget(self.open_button); layout.addLayout(footer)
        self.search_timer = QTimer(self.search); self.search_timer.setSingleShot(True); self.search_timer.setInterval(120); self.search_timer.timeout.connect(self.render_history)
        self.search.textChanged.connect(lambda *_: self.search_timer.start())
        for box in (self.history_folder, self.status_filter, self.date_filter): box.currentIndexChanged.connect(self.render_history)

    def render_history(self, *_):
        if getattr(self, '_background', False):
            self._history_dirty = True
            return
        query = self.search.text().strip().casefold(); folder = self.history_folder.currentData(); self._filter_folder = folder
        status = self.status_filter.currentData(); date = self.date_filter.currentData(); now = datetime.now().astimezone()
        selected = self.selected_event() if hasattr(self, '_history_rows') else None
        results = []
        for event in reversed(self.settings.history):
            if query and query not in Path(event['source']).name.casefold(): continue
            if folder and Path(event['source']).parent != Path(folder) and Path(event['source']) != Path(folder): continue
            if status and event['status'] != status: continue
            if date != 'all_dates':
                try: stamp = datetime.fromisoformat(event['time']).astimezone()
                except ValueError: continue
                if date == 'today' and stamp.date() != now.date(): continue
                if date == 'week' and not now - timedelta(days=7) <= stamp <= now: continue
            results.append(event)
        self._history_rows = results
        listing = self.history_table; listing.blockSignals(True); listing.setUpdatesEnabled(False); listing.replace(results)
        self.activity_cards = []
        if selected in results: listing.setCurrentRow(results.index(selected))
        listing.blockSignals(False); listing.setUpdatesEnabled(True)
        listing.setVisible(bool(results)); self.history_empty.setVisible(not results)
        self.empty_spacer.setVisible(not results)
        self.history_summary.setText(self.t('history_count', n=len(results), total=len(self.settings.history)))
        self.history_selection(); self.render_recent()

    def selected_event(self):
        item = self.history_table.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item and self.history_table.selectedItems() else None

    def history_selection(self):
        event = self.selected_event()
        self.open_button.setEnabled(bool(event and event['status'] == 'success' and event['destination']))
        card = self.history_table.show_details() if event else self.history_table.card
        self.activity_cards = [card] if card else []
        for index, card in enumerate(getattr(self, 'activity_cards', [])):
            selected = event is not None and card.event == event
            card.set_selected(selected)
            if selected:
                card.expand_button.setChecked(True)
                self.history_details = card.details_text

    def render_recent(self):
        self.clear_layout(self.recent_layout)
        for event in list(reversed(self.settings.history))[:3]:
            row = QWidget(); line = QHBoxLayout(row); line.setContentsMargins(0, 5, 0, 5); line.setSpacing(10)
            line.addWidget(badge(category_for(event['source']), size=30))
            copy = QVBoxLayout(); copy.setSpacing(1)
            filename = ElideLabel(Path(event['source']).name, 'cardTitle'); filename.setAlignment(Qt.AlignmentFlag.AlignRight if self.settings.language == 'ar' else Qt.AlignmentFlag.AlignLeft)
            filename.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            filename.setProperty('ffFileName', True)
            copy.addWidget(filename)
            caption = text(timestamp(event['time'], self.settings.language), 'micro'); caption.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.settings.language == 'ar' else Qt.LayoutDirection.LeftToRight)
            caption.setProperty('ffTimestamp', event['time'])
            copy.addWidget(caption); line.addLayout(copy, 1); line.addWidget(StatusPill(self.t(event['status']), event['status']))
            self.recent_layout.addWidget(row)
        if not self.settings.history: self.recent_layout.addWidget(text(self.t('history_empty'), 'muted', True))

    def apply_theme(self):
        dark = self.settings.theme == 'dark'
        bg, panel, side, fg, muted, border = ('#14171d', '#1d222b', '#191d25', '#ebeff7', '#98a5b9', '#2b3340') if dark else ('#f7f8fb', '#ffffff', '#eff2f7', '#25314a', '#78859a', '#e7ebf2')
        selected = '#24334e' if dark else '#edf3ff'
        sheet = f'''
        QWidget {{color:{fg};font-family:'Segoe UI';font-size:13px;}}
        QMainWindow,QScrollArea,QScrollArea > QWidget > QWidget,QStackedWidget {{background:{bg};}}
        QLabel {{background:transparent;}}
        QLabel#brand {{font-size:21px;font-weight:700;}}
        QLabel#hero {{font-size:25px;font-weight:600;}}
        QLabel#section {{font-size:16px;font-weight:600;}}
        QLabel#cardTitle,QLabel#ruleValue {{font-size:13px;font-weight:600;}}
        QLabel#ruleValue {{font-size:17px;}}
        QLabel#muted,QLabel#folderCaption {{color:{muted};}}
        QLabel#micro,QLabel#eyebrow {{color:{muted};font-size:11px;}}
        QLabel#route {{color:{muted};font-size:11px;}}
        QLabel#extensionBadge {{color:{muted};font-size:10px;background:{side};border-radius:4px;padding:2px 5px;}}
        QLabel#error {{color:#d98974;}}
        QFrame#sidebar {{background:{side};border:0;}}
        QFrame#panel,QFrame#categoryCard,QFrame#ruleCard,QFrame#folderCard,QFrame#recentPanel,QFrame#activityCard,QFrame#emptyState {{background:{panel};border:1px solid {border};border-radius:13px;}}
        QFrame#folderCard[selected="true"],QFrame#activityCard[selected="true"] {{background:{selected};border-color:#6a91d7;}}
        QFrame#ruleCard[enabledRule="false"] {{border-style:dashed;}}
        QPushButton {{background:{panel};border:1px solid {border};border-radius:8px;padding:6px 11px;font-weight:600;}}
        QPushButton:focus {{border:2px solid #86a7e9;}}
        QPushButton:pressed {{background:#496897;color:white;}}
        QPushButton:disabled {{color:{muted};background:transparent;}}
        QPushButton#primary {{background:#3978ee;border:1px solid #3978ee;color:white;padding:10px 18px;}}
        QPushButton#primary:disabled {{background:#6e82a5;border-color:#6e82a5;}}
        QPushButton#quiet,QPushButton#iconButton,QPushButton#folderTitle,QPushButton#activityTitle {{background:transparent;border-color:transparent;color:{muted};}}
        QPushButton#activityTitle {{color:{fg};padding:0;text-align:left;min-height:24px;}}
        QPushButton#folderTitle {{font-size:16px;color:{fg};text-align:left;}}
        QPushButton#inlineAction {{background:transparent;color:#6495f5;border-color:transparent;}}
        QPushButton#inlineAction:disabled {{color:{muted};}}
        QPushButton#danger {{color:#c27d78;background:transparent;border-color:transparent;}}
        QPushButton#navigation {{background:transparent;border:0;text-align:left;padding:9px 12px;color:{muted};}}
        QPushButton#navigation:checked {{background:{selected};color:#7198e8;}}
        QPushButton#navigation:focus {{border:1px solid #86a7e9;}}
        QPushButton#navigation:right-to-left,QPushButton#folderTitle:right-to-left {{text-align:right;}}
        QPushButton#navigation:left-to-right,QPushButton#folderTitle:left-to-right {{text-align:left;}}
        QPushButton#activityTitle[uiRtl="true"] {{text-align:right;}}
        QPushButton#activityTitle[uiRtl="false"] {{text-align:left;}}
        QPushButton::menu-indicator {{width:0;height:0;}}
        QListWidget,QListView {{background:transparent;border:0;outline:0;}}
        QListWidget#folderList::item {{padding:9px;border-radius:7px;}}
        QListWidget#folderList::item:selected {{background:{selected};color:{fg};}}
        QListWidget#activityList::item {{background:transparent;border:0;}}
        QListWidget#activityList::item:selected {{background:transparent;}}
        QLineEdit,QComboBox {{background:{panel};border:1px solid {border};border-radius:8px;padding:7px 9px;min-height:18px;selection-background-color:#3978ee;}}
        QLineEdit:focus,QComboBox:focus {{border-color:#7299e5;}}
        QLineEdit#pathField {{background:transparent;color:{muted};border:0;border-radius:5px;padding:4px 0;font-size:12px;}}
        QLineEdit#pathField:focus {{background:{selected};}}
        QComboBox::drop-down {{background:transparent;border:0;width:24px;}}
        QComboBox::down-arrow {{width:8px;height:8px;}}
        QComboBox QAbstractItemView {{background:{panel};color:{fg};selection-background-color:{selected};border:1px solid {border};outline:0;}}
        QFrame#statusPill {{background:{side};border:0;border-radius:10px;}}
        QFrame#statusPill QLabel {{font-size:11px;color:{muted};}}
        QFrame#statusPill[tone="success"] {{background:{'#20392f' if dark else '#eaf5ef'};}}
        QFrame#statusPill[tone="success"] QLabel {{color:{'#8fc4a9' if dark else '#458465'};}}
        QFrame#statusPill[tone="error"] {{background:{'#3b2b2b' if dark else '#faeded'};}}
        QFrame#statusPill[tone="error"] QLabel {{color:{'#d8a09a' if dark else '#b26f67'};}}
        QFrame#statusPill[tone="deferred"] QLabel {{color:#bc9a60;}}
        QProgressBar {{background:{border};border:0;}}
        QProgressBar::chunk {{background:#3978ee;}}
        QDialog,QMessageBox,QMenu {{background:{panel};}}
        QMenu {{padding:5px;border:1px solid {border};}}
        QMenu::item {{padding:9px 20px;}}
        QMenu::item:selected {{background:{selected};}}
        QScrollArea {{border:0;}}
        QScrollBar:vertical {{background:transparent;width:8px;}}
        QScrollBar::handle:vertical {{background:{border};border-radius:4px;min-height:32px;}}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        QToolTip {{background:{panel};color:{fg};border:1px solid {border};padding:7px;}}
        QFrame#toast {{background:{panel};border:1px solid #7299e5;border-radius:12px;}}
        QFrame#toast[warning="true"] {{border-color:#c48c55;}}
        '''
        if self.styleSheet() != sheet: self.setStyleSheet(sheet)
        for widget in self.findChildren(Switch): widget.setProperty('dark', dark); widget.update()
        if hasattr(self, 'history_table'): self.history_table.viewport().update()
