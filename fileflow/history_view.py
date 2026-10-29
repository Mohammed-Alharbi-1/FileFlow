"""Viewport-painted history with one accessible native detail card on selection."""
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QSize, QRect, Signal, QEvent, QAbstractAnimation
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QListView, QStyledItemDelegate, QAbstractItemView, QStyle
from .visuals import vector_icon, category_for, timestamp, ActivityCard, COLORS


class HistoryModel(QAbstractListModel):
    def __init__(self, parent):
        super().__init__(parent); self.records=[]; self.heights={}

    def rowCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.records)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.records): return None
        event=self.records[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.AccessibleTextRole):
            return Path(event['source']).name
        if role == Qt.ItemDataRole.UserRole: return event
        if role == Qt.ItemDataRole.AccessibleDescriptionRole:
            owner=self.parent().owner
            return f"{owner.t(event['status'])}. {event['time']}. {event['source']}. {event['destination']}"
        if role == Qt.ItemDataRole.ToolTipRole: return event['source']
        if role == Qt.ItemDataRole.SizeHintRole: return QSize(0,self.heights.get(index.row(),126))

    def replace(self, records):
        self.beginResetModel(); self.records=list(records); self.heights.clear(); self.endResetModel()


class HistoryItem:
    def __init__(self, view, row): self.view,self.row=view,row
    def data(self, role): return self.view.model().data(self.view.model().index(self.row),role)
    def text(self): return self.data(Qt.ItemDataRole.DisplayRole)
    def sizeHint(self): return self.data(Qt.ItemDataRole.SizeHintRole)
    def setSizeHint(self, size):
        model=self.view.model(); model.heights[self.row]=size.height()
        index=model.index(self.row); model.dataChanged.emit(index,index,[Qt.ItemDataRole.SizeHintRole]); self.view.scheduleDelayedItemsLayout()


class HistoryDelegate(QStyledItemDelegate):
    def __init__(self, view): super().__init__(view); self.view=view
    def sizeHint(self, option, index): return index.data(Qt.ItemDataRole.SizeHintRole)
    def paint(self, painter, option, index):
        view=self.view; owner=view.owner; event=index.data(Qt.ItemDataRole.UserRole)
        if view.card is not None and view.card.item.row == index.row(): return
        dark=owner.settings.theme=='dark'; rtl=owner.settings.language=='ar'
        panel='#1d222b' if dark else '#ffffff'; border='#2b3340' if dark else '#e7ebf2'
        fg='#ebeff7' if dark else '#25314a'; muted='#98a5b9' if dark else '#78859a'
        rect=option.rect.adjusted(1,2,-1,-3); painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#6a91d7' if option.state & QStyle.StateFlag.State_HasFocus else border)))
        painter.setBrush(QColor(panel)); painter.drawRoundedRect(rect,13,13)
        def logical(x,y,w,h):
            return QRect(rect.right()-x-w if rtl else rect.left()+x, rect.top()+y,w,h)
        category=category_for(event['source']); tint=COLORS[category]; tile=logical(14,12,34,34)
        color=QColor(tint); color.setAlpha(24); painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(color); painter.drawRoundedRect(tile,10,10)
        vector_icon(category,tint).paint(painter,tile.adjusted(7,7,-7,-7))
        align=Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft
        title=logical(58,10,max(40,rect.width()-220),25)
        font=QFont(owner.font()); font.setPixelSize(13); font.setWeight(QFont.Weight.DemiBold); painter.setFont(font); painter.setPen(QColor(fg))
        painter.drawText(title,align|Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(Path(event['source']).name,Qt.TextElideMode.ElideMiddle,title.width()))
        font.setPixelSize(11); font.setWeight(QFont.Weight.Normal); painter.setFont(font); painter.setPen(QColor(muted))
        painter.drawText(logical(58,36,max(40,rect.width()-220),22),align|Qt.AlignmentFlag.AlignVCenter,timestamp(event['time'],owner.settings.language)+'  '+Path(event['source']).suffix.lstrip('.').upper())
        status=owner.t(event['status']); status_width=min(150,painter.fontMetrics().horizontalAdvance(status)+30)
        status_rect=logical(max(14,rect.width()-status_width-14),18,status_width,25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(('#20392f' if dark else '#eaf5ef') if event['status']=='success' else ('#3b2b2b' if dark else '#faeded')))
        painter.drawRoundedRect(status_rect,10,10)
        painter.setPen(QColor('#bc9a60') if event['status']=='deferred' else QColor('#8fc4a9' if dark else '#458465') if event['status']=='success' else QColor('#d8a09a' if dark else '#b26f67'))
        painter.drawText(status_rect,Qt.AlignmentFlag.AlignCenter,'●  '+status)
        font.setPixelSize(13); painter.setFont(font)
        painter.setPen(QColor(muted)); painter.drawText(logical(14,76,160,34),align|Qt.AlignmentFlag.AlignVCenter,owner.t('details'))
        painter.setPen(QColor('#6495f5' if event['status']=='success' else muted))
        vector_icon('open').paint(painter,logical(rect.width()-174,85,16,16))
        painter.drawText(logical(rect.width()-152,76,138,34),align|Qt.AlignmentFlag.AlignVCenter,owner.t('open'))
        painter.restore()
    def editorEvent(self, event, model, option, index):
        if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton:
            rtl=self.view.owner.settings.language=='ar'; x=event.position().x()-option.rect.left()
            if rtl: x=option.rect.width()-x
            if event.position().y()-option.rect.top()>72 and x>option.rect.width()-180:
                self.view.owner.open_event(index.data(Qt.ItemDataRole.UserRole)); return True
        return super().editorEvent(event,model,option,index)


class HistoryView(QListView):
    itemSelectionChanged=Signal()
    itemDoubleClicked=Signal(object)
    def __init__(self, owner):
        super().__init__(); self.owner=owner; self.card=None
        self.setModel(HistoryModel(self)); self.setItemDelegate(HistoryDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.selectionModel().selectionChanged.connect(lambda *_:self.itemSelectionChanged.emit())
        self.doubleClicked.connect(lambda index:self.itemDoubleClicked.emit(self.item(index.row())))
    def count(self): return self.model().rowCount()
    def rowCount(self): return self.count()
    def item(self,row,column=0): return HistoryItem(self,row) if 0<=row<self.count() else None
    def currentItem(self): return self.item(self.currentIndex().row()) if self.currentIndex().isValid() else None
    def selectedItems(self): return [self.item(index.row()) for index in self.selectionModel().selectedIndexes()]
    def setCurrentCell(self,row,column=0): self.setCurrentRow(row)
    def setCurrentRow(self,row): self.setCurrentIndex(self.model().index(row))
    def setCurrentItem(self,item): self.setCurrentRow(item.row)
    def replace(self,records):
        if self.card:
            for animation in self.card.findChildren(QAbstractAnimation): animation.stop()
        self.card=None; self.model().replace(records)
    def show_details(self):
        index=self.currentIndex()
        if not index.isValid(): return None
        if self.card is not None and self.card.item.row==index.row(): return self.card
        if self.card is not None:
            for animation in self.card.findChildren(QAbstractAnimation): animation.stop()
            old=self.card.item.row; self.model().heights.pop(old,None)
            self.setIndexWidget(self.model().index(old),None)
            old_index=self.model().index(old); self.model().dataChanged.emit(old_index,old_index,[Qt.ItemDataRole.SizeHintRole])
        item=self.item(index.row()); self.card=ActivityCard(self.owner,item.data(Qt.ItemDataRole.UserRole),item,self)
        self.setIndexWidget(index,self.card); self.card.set_selected(True)
        return self.card
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter): self.owner.open_selected(); event.accept(); return
        if event.key()==Qt.Key.Key_Space:
            card=self.show_details()
            if card: card.expand_button.toggle()
            event.accept(); return
        super().keyPressEvent(event)
