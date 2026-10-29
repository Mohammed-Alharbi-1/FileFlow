"""Small native controls. Qt owns input, focus, checked state, and accessibility."""
import os
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve, QRectF, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QPushButton, QFrame, QHBoxLayout, QLabel, QGraphicsOpacityEffect


def motion_duration():
    if os.environ.get('FILEFLOW_REDUCED_MOTION') == '1':
        return 0
    if os.name == 'nt':
        import ctypes
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0) and not enabled.value:
            return 0
    return 180


class HoverButton(QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._hover = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.animation = QPropertyAnimation(self, b'hoverAmount', self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_hover(self): return self._hover
    def set_hover(self, value):
        self._hover = value
        self.update()
    hoverAmount = Property(float, get_hover, set_hover)

    def animate(self, target):
        self.animation.stop()
        self.animation.setDuration(motion_duration())
        self.animation.setStartValue(self._hover)
        self.animation.setEndValue(target)
        self.animation.start()

    def enterEvent(self, event):
        self.animate(1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animate(0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(56, 123, 246, int(22 * self._hover) if self.isEnabled() else 0))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 9, 9)


class CheckBox(QCheckBox):
    switch = False

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._position = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(40)
        self.animation = QPropertyAnimation(self, b'position', self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self.animate)

    def hitButton(self, point):
        return self.rect().contains(point)

    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + (66 if self.switch else 38), 40)

    def get_position(self): return self._position
    def set_position(self, value):
        self._position = value
        self.update()
    position = Property(float, get_position, set_position)

    def animate(self, checked):
        self.animation.stop()
        self.animation.setDuration(motion_duration() if self.isVisible() else 0)
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.property('dark') is True
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        width = 42 if self.switch else 20
        x = self.width() - width - 5 if rtl else 5
        box = QRectF(x, (self.height() - (24 if self.switch else 20)) / 2, width, 24 if self.switch else 20)
        p.setOpacity(1 if self.isEnabled() else .4)
        p.setPen(QPen(QColor('#65809a' if dark else '#b9c4d2'), 1))
        p.setBrush(QColor('#3478f6' if self.isChecked() else ('#46505e' if dark else '#d7dde5')))
        p.drawRoundedRect(box, 12 if self.switch else 5, 12 if self.switch else 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('white'))
        if self.switch:
            fraction = 1 - self._position if rtl else self._position
            p.drawEllipse(QRectF(box.x() + 3 + fraction * 18, box.y() + 3, 18, 18))
        elif self.isChecked():
            p.setPen(QPen(QColor('white'), 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(x + 5), int(box.y() + 10), int(x + 9), int(box.y() + 14))
            p.drawLine(int(x + 9), int(box.y() + 14), int(x + 16), int(box.y() + 6))
        text_rect = self.rect().adjusted(5 if rtl else width + 16, 0, -width - 16 if rtl else -5, 0)
        p.setPen(QColor('#ecf0f6' if dark else '#243047'))
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(text_rect, (Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter, text)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#3478f6'), 2, Qt.PenStyle.DotLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 7, 7)


class Switch(CheckBox):
    switch = True


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = 0.0
        self.animation = QPropertyAnimation(self, b'hoverAmount', self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_hover(self): return self._hover
    def set_hover(self, value):
        self._hover = value
        self.update()
    hoverAmount = Property(float, get_hover, set_hover)

    def transition(self, value):
        self.animation.stop()
        self.animation.setDuration(motion_duration())
        self.animation.setStartValue(self._hover)
        self.animation.setEndValue(value)
        self.animation.start()

    def enterEvent(self, event):
        self.transition(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.transition(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(52, 120, 246, int(self._hover * 100)), 1.4))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 12, 12)
        # A restrained painted shadow avoids nesting graphics effects in page fades.
        painter.setPen(QPen(QColor(0, 0, 0, 9), 1))
        painter.drawLine(12, self.height() - 2, self.width() - 12, self.height() - 2)


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('toast')
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 12, 12, 12)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        row.addWidget(self.message, 1)
        dismiss = HoverButton('×')
        dismiss.setAccessibleName(parent.window().t('dismiss'))
        dismiss.setFixedWidth(36)
        dismiss.clicked.connect(self.hide)
        row.addWidget(dismiss)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b'opacity', self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        self.animation.finished.connect(self.finished)
        self.hiding = False
        self.hide()

    def anchor(self):
        width = min(500, self.parentWidget().width() - 48)
        self.setFixedWidth(width)
        self.adjustSize()
        self.move((self.parentWidget().width() - width) // 2, 18)

    def notify(self, text, warning=False):
        self.animation.stop()
        self.hiding = False
        self.setProperty('warning', warning)
        self.style().unpolish(self)
        self.style().polish(self)
        self.message.setText(text)
        self.anchor()
        self.show()
        self.raise_()
        self.animation.setDuration(motion_duration())
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()
        self.timer.start(6000 if warning else 4000)

    def fade_out(self):
        self.animation.stop()
        self.hiding = True
        self.animation.setDuration(motion_duration())
        self.animation.setStartValue(self.effect.opacity())
        self.animation.setEndValue(0.0)
        self.animation.start()

    def finished(self):
        if self.hiding:
            self.hide()
