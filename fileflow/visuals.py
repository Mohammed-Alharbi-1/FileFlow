"""Original vector marks, typography helpers and native expanding activity rows."""
from datetime import datetime
import unicodedata
from functools import lru_cache
from PySide6.QtCore import Qt, QSize, QRectF, QPointF, QLocale, QDateTime, QPropertyAnimation, QEasingCurve, Signal, Property
from PySide6.QtGui import QPainter, QPen, QColor, QIcon, QPixmap, QPainterPath
from PySide6.QtWidgets import QLabel, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QSizePolicy, QComboBox
from .controls import Card, HoverButton, motion_duration
from .models import CATEGORIES
from .localization import bind


@lru_cache(maxsize=128)
def vector_icon(name, color='#718199', size=20):
    """Draw our own 24-unit line icons; never load external icon collections."""
    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24, size / 24)
    p.setPen(QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if name in ('folders', 'folder', 'open'):
        path = QPainterPath(QPointF(3, 7)); path.lineTo(3, 19); path.quadTo(3, 21, 5, 21); path.lineTo(19, 21); path.quadTo(21, 21, 21, 19); path.lineTo(21, 9); path.quadTo(21, 7, 19, 7); path.lineTo(11, 7); path.lineTo(9, 4); path.lineTo(5, 4); path.quadTo(3, 4, 3, 7); p.drawPath(path)
    elif name == 'dashboard':
        for x, y in ((4, 4), (14, 4), (4, 14), (14, 14)): p.drawRoundedRect(x, y, 6, 6, 2, 2)
    elif name in ('history', 'clock'):
        p.drawEllipse(4, 4, 16, 16); p.drawLine(12, 7, 12, 12); p.drawLine(12, 12, 16, 14)
    elif name in ('rules', 'settings'):
        for y, x in ((6, 8), (12, 16), (18, 10)):
            p.drawLine(3, y, x - 3, y); p.drawLine(x + 3, y, 21, y); p.drawEllipse(QPointF(x, y), 2.5, 2.5)
    elif name == 'Images':
        p.drawRoundedRect(3, 4, 18, 16, 3, 3); p.drawEllipse(6, 7, 3, 3); p.drawPolyline([QPointF(4, 18), QPointF(10, 12), QPointF(14, 16), QPointF(17, 13), QPointF(20, 17)])
    elif name == 'Videos':
        p.drawRoundedRect(3, 6, 13, 13, 3, 3); p.drawPolyline([QPointF(16, 10), QPointF(21, 7), QPointF(21, 18), QPointF(16, 15)])
    elif name == 'Audio':
        p.drawLine(10, 16, 10, 5); p.drawLine(10, 5, 19, 3); p.drawLine(19, 3, 19, 14); p.drawEllipse(4, 15, 6, 5); p.drawEllipse(13, 13, 6, 5)
    elif name == 'Archives':
        p.drawRoundedRect(4, 4, 16, 17, 3, 3); p.drawLine(4, 9, 20, 9); p.drawLine(10, 13, 14, 13); p.drawLine(12, 13, 12, 17)
    elif name == 'Installers':
        p.drawRoundedRect(3, 4, 18, 16, 3, 3); p.drawLine(12, 7, 12, 15); p.drawPolyline([QPointF(8, 12), QPointF(12, 16), QPointF(16, 12)])
    elif name in ('edit', 'pencil'):
        p.drawPolyline([QPointF(5, 15), QPointF(16, 4), QPointF(20, 8), QPointF(9, 19), QPointF(4, 20), QPointF(5, 15)]); p.drawLine(14, 6, 18, 10)
    elif name == 'chevron':
        p.drawPolyline([QPointF(8, 5), QPointF(15, 12), QPointF(8, 19)])
    elif name == 'more':
        for x in (5, 12, 19): p.drawEllipse(QPointF(x, 12), 1, 1)
    elif name == 'search':
        p.drawEllipse(4, 4, 12, 12); p.drawLine(15, 15, 21, 21)
    else:
        path = QPainterPath(QPointF(6, 3)); path.lineTo(14, 3); path.lineTo(20, 9); path.lineTo(20, 20); path.quadTo(20, 21, 18, 21); path.lineTo(6, 21); path.quadTo(4, 21, 4, 19); path.lineTo(4, 5); path.quadTo(4, 3, 6, 3); p.drawPath(path); p.drawLine(14, 3, 14, 9); p.drawLine(14, 9, 20, 9); p.drawLine(8, 13, 16, 13); p.drawLine(8, 17, 14, 17)
    p.end()
    return QIcon(pix)


COLORS = {'Images': '#7d76d8', 'Documents': '#4d87d9', 'Videos': '#c37697', 'Audio': '#bf9354', 'Archives': '#669e8d', 'Installers': '#7f91aa', 'Other Files': '#8d92a3'}


def badge(name, color=None, size=34):
    result = QLabel()
    result.setObjectName('iconTile')
    result.setFixedSize(size, size)
    tint = color or COLORS.get(name, '#678bd5')
    color = QColor(tint)
    result.setStyleSheet(f'background:rgba({color.red()},{color.green()},{color.blue()},24);border-radius:10px;')
    result.setAlignment(Qt.AlignmentFlag.AlignCenter)
    result.setPixmap(vector_icon(name, tint, 20).pixmap(20, 20))
    return result


def category_for(path):
    from pathlib import Path
    suffix = Path(path).suffix.lower().lstrip('.')
    return next((category for category, extensions in CATEGORIES.items() if suffix in extensions), 'Other Files')


def direction(text):
    for character in text:
        bidi = unicodedata.bidirectional(character)
        if bidi in ('R', 'AL'): return Qt.LayoutDirection.RightToLeft
        if bidi == 'L': return Qt.LayoutDirection.LeftToRight
    return Qt.LayoutDirection.LeftToRight


class ElideLabel(QLabel):
    def __init__(self, text='', name=''):
        super().__init__()
        self.full_text = text
        self.setObjectName(name)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setToolTip(text)
        self.setLayoutDirection(direction(text))
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(20)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideMiddle, self.width()))


def path_field(path):
    """Raw strings stay raw: copying never includes bidi control characters."""
    result = QLineEdit(path)
    result.setReadOnly(True)
    result.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    result.setObjectName('pathField')
    result.setToolTip(path)
    result.setCursorPosition(0)
    result.setMinimumWidth(0)
    return result


def timestamp(value, language):
    try:
        local = datetime.fromisoformat(value).astimezone()
        stamp = QDateTime(local)
        return QLocale('ar_SA' if language == 'ar' else 'en_GB').toString(stamp, 'dd MMM yyyy  ·  hh:mm AP')
    except (ValueError, TypeError):
        return value


class StatusPill(QFrame):
    def __init__(self, text='', tone='neutral'):
        super().__init__()
        self.setObjectName('statusPill')
        row = QHBoxLayout(self); row.setContentsMargins(9, 4, 9, 4); row.setSpacing(6)
        self.dot = QLabel('●'); self.dot.setObjectName('statusDot'); row.addWidget(self.dot)
        self.caption = QLabel(text); self.caption.setTextFormat(Qt.TextFormat.PlainText); bind(self.caption, text); row.addWidget(self.caption)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setTone(tone)

    def setText(self, text): self.caption.setText(text); bind(self.caption, text)
    def text(self): return self.caption.text()
    def setTone(self, tone):
        self.setProperty('tone', tone)
        self.style().unpolish(self); self.style().polish(self)


class FilterCombo(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#8390a6'), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = 14 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width() - 16
        y = self.height() / 2
        painter.drawPolyline([QPointF(x - 3, y - 1.5), QPointF(x, y + 1.5), QPointF(x + 3, y - 1.5)])


class ActivityList(QListWidget):
    """Native list with row-based selection; small compatibility methods for callers."""
    def rowCount(self): return self.count()
    def item(self, row, column=0): return super().item(row)
    def setCurrentCell(self, row, column=0): self.setCurrentRow(row)


class ActivityTitle(HoverButton):
    doubleActivated = Signal()

    def mouseDoubleClickEvent(self, event):
        self.doubleActivated.emit()
        event.accept()


class ActivityCard(Card):
    def __init__(self, owner, event, item, listing):
        super().__init__()
        from pathlib import Path
        self.owner, self.event, self.item, self.listing = owner, event, item, listing
        self._selection = 0.0
        self.selection_animation = QPropertyAnimation(self, b'selectionAmount', self)
        self.selection_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setObjectName('activityCard')
        self.layout_box = QVBoxLayout(self); self.layout_box.setContentsMargins(14, 10, 14, 10); self.layout_box.setSpacing(8)
        top = QHBoxLayout(); top.setSpacing(10)
        category = category_for(event['source'])
        top.addWidget(badge(category))
        copy = QVBoxLayout(); copy.setSpacing(2)
        self.name_button = ActivityTitle(Path(event['source']).name or event['source']); self.name_button.setObjectName('activityTitle')
        self.name_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.name_button.setToolTip(event['source']); self.name_button.setAccessibleName(Path(event['source']).name)
        self.name_button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.name_button.setProperty('uiRtl', owner.settings.language == 'ar')
        self.name_button.clicked.connect(self.select_and_expand)
        self.name_button.doubleActivated.connect(lambda: owner.open_event(event))
        copy.addWidget(self.name_button)
        metadata = timestamp(event['time'], owner.settings.language)
        extension = Path(event['source']).suffix.lstrip('.').upper()
        stamp = QLabel(metadata); stamp.setObjectName('micro')
        self.timestamp_label = stamp
        stamp.setLayoutDirection(Qt.LayoutDirection.RightToLeft if owner.settings.language == 'ar' else Qt.LayoutDirection.LeftToRight)
        metadata_row = QHBoxLayout(); metadata_row.setSpacing(8); metadata_row.addWidget(stamp)
        if extension:
            extension_label = QLabel(extension); extension_label.setObjectName('extensionBadge'); extension_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight); metadata_row.addWidget(extension_label)
        metadata_row.addStretch(); copy.addLayout(metadata_row)
        top.addLayout(copy, 1)
        self.status = StatusPill(owner.t(event['status']), event['status']); top.addWidget(self.status)
        self.layout_box.addLayout(top)
        actions = QHBoxLayout(); actions.setSpacing(6)
        self.expand_button = HoverButton(owner.t('details')); self.expand_button.setObjectName('quiet'); self.expand_button.setCheckable(True)
        self.expand_button.toggled.connect(self.expand)
        actions.addWidget(self.expand_button)
        actions.addStretch()
        self.open_action = HoverButton(owner.t('open')); self.open_action.setObjectName('inlineAction'); self.open_action.setIcon(vector_icon('open'))
        self.open_action.setEnabled(event['status'] == 'success' and bool(event['destination']))
        self.open_action.clicked.connect(lambda: owner.open_event(event)); actions.addWidget(self.open_action)
        self.layout_box.addLayout(actions)
        self.reveal = QWidget(); self.reveal.setMaximumHeight(0); self.reveal.setMinimumHeight(0)
        self.reveal_box = QVBoxLayout(self.reveal); self.reveal_box.setContentsMargins(0, 4, 0, 0); self.reveal_box.setSpacing(5)
        self.layout_box.addWidget(self.reveal)
        self.reveal_animation = QPropertyAnimation(self.reveal, b'maximumHeight', self)
        self.reveal_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.reveal_animation.valueChanged.connect(self.update_size)
        self.details_text = QLabel(self.reveal); self.details_text.setWordWrap(True); self.details_text.setTextFormat(Qt.TextFormat.PlainText)
        self.details_text.hide()
        self.details_text.setObjectName('muted')
        self.details_built = False
        self.base_height = 126
        self.item.setSizeHint(QSize(0, self.base_height))

    def select_and_expand(self):
        self.listing.setCurrentItem(self.item)
        self.expand_button.setChecked(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.listing.setCurrentItem(self.item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.owner.open_event(self.event)
        event.accept()

    def expand(self, expanded):
        if not self.details_built:
            for key in ('source', 'destination'):
                caption = QLabel(self.owner.t(key)); bind(caption, self.owner.t(key)); caption.setObjectName('eyebrow'); self.reveal_box.addWidget(caption)
                caption.ensurePolished(); caption.show()
                field = path_field(self.event[key] or '—'); field.setAccessibleName(self.owner.t(key)); self.reveal_box.addWidget(field)
                field.ensurePolished(); field.show()
            self.details_text.setText(self.owner.t(self.event['detail']) if self.event['detail'] else self.owner.t(self.event['status']))
            self.reveal_box.addWidget(self.details_text)
            self.details_text.ensurePolished(); self.details_text.show()
            self.details_built = True
        self.expand_button.setText(self.owner.t('less_details' if expanded else 'details'))
        self.reveal_box.invalidate(); self.reveal_box.activate()
        height = self.reveal_box.heightForWidth(max(100, self.width() - 28)) if self.reveal_box.hasHeightForWidth() else self.reveal_box.sizeHint().height()
        self.reveal_animation.stop(); self.reveal_animation.setDuration(motion_duration())
        self.reveal_animation.setStartValue(self.reveal.maximumHeight())
        self.reveal_animation.setEndValue(height + 8 if expanded else 0)
        self.reveal_animation.start()

    def update_size(self, value):
        self.item.setSizeHint(QSize(0, self.base_height + int(value)))

    def set_selected(self, selected):
        if bool(self.property('selected')) == selected:
            return
        self.setProperty('selected', selected)
        self.style().unpolish(self); self.style().polish(self)
        self.selection_animation.stop(); self.selection_animation.setDuration(motion_duration())
        self.selection_animation.setStartValue(self._selection); self.selection_animation.setEndValue(1.0 if selected else 0.0); self.selection_animation.start()

    def refresh_locale(self):
        rtl = self.owner.settings.language == 'ar'
        self.timestamp_label.setText(timestamp(self.event['time'], self.owner.settings.language))
        self.timestamp_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        self.status.setText(self.owner.t(self.event['status']))
        self.open_action.setText(self.owner.t('open'))
        self.expand_button.setText(self.owner.t('less_details' if self.expand_button.isChecked() else 'details'))
        if self.name_button.property('uiRtl') != rtl:
            self.name_button.setProperty('uiRtl', rtl)
            self.name_button.style().unpolish(self.name_button); self.name_button.style().polish(self.name_button)
        if self.details_built:
            self.details_text.setText(self.owner.t(self.event['detail']) if self.event['detail'] else self.owner.t(self.event['status']))
            # Re-measure without collapsing/recreating the currently expanded panel.
            if self.expand_button.isChecked(): self.expand(True)

    def get_selection(self): return self._selection
    def set_selection(self, value): self._selection = value; self.update()
    selectionAmount = Property(float, get_selection, set_selection)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(92, 138, 220, int(120 * self._selection)), 1.2))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 13, 13)
