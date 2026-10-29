import threading
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLineEdit
from PySide6.QtTest import QTest
from fileflow.engine import Activity
from fileflow.history_view import HistoryModel, HistoryView
from fileflow.visuals import ActivityCard
from test_overhaul import window
from test_service_ui import until, fast_service


def settle():
    QTest.qWait(20); QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)


def fill(window, count=200):
    event=window.settings.history[0]
    window.settings.history=[dict(event,source=str(Path(event['source']).parent/f'record-{n}.pdf')) for n in range(count)]
    window.render_history(); window.navigate('history',animate=False); settle()


def test_history_uses_model_and_only_one_native_card(window, qapp):
    fill(window)
    assert isinstance(window.history_table,HistoryView)
    assert isinstance(window.history_table.model(),HistoryModel)
    assert window.history_table.model().rowCount()==200
    assert not window.history_table.findChildren(ActivityCard)
    baseline=len(qapp.allWidgets())
    for row in (0,199,58,17,0):
        window.history_table.setCurrentCell(row,0); settle()
        assert len(window.history_table.findChildren(ActivityCard))==1
        assert len(qapp.allWidgets())<baseline+35
        assert window.selected_event()['source'].endswith(f'record-{199-row}.pdf')
        fields=window.activity_cards[0].reveal.findChildren(QLineEdit)
        fields[0].selectAll(); fields[0].copy()
        assert QApplication.clipboard().text()==window.selected_event()['source']
        window.activity_cards[0].expand_button.setChecked(False); settle()
    assert window.store.load().history != []


def test_hidden_activity_is_persisted_without_rebuilding_view(window,qapp,monkeypatch):
    fast_service(monkeypatch); fill(window)
    model=window.history_table.model(); original=list(model.records)
    window.hide(); settle()
    for n in range(220):
        window.on_activity(Activity(str(Path(window.selected_path)/f'background-{n}.txt'),status='error',detail='test'))
    assert model.records==original
    assert len(window.settings.history)==200
    window.on_completed(0,220,False)
    assert len(window.store.load().history)==200
    assert not window.activity_timer.isActive() if hasattr(window,'activity_timer') else True
    window.restore(); settle()
    assert model is window.history_table.model()
    assert len(model.records)==200 and 'background' in model.records[0]['source']


def test_fifty_hide_restore_and_history_interactions_are_bounded(window,qapp):
    fill(window); threads=len(threading.enumerate()); worker=window.service._thread
    for cycle in range(50):
        window.history_table.setCurrentCell(cycle%200,0); settle()
        window.hide(); window.restore(); settle()
        assert window.history_table.model().rowCount()==200
        assert window.service._thread is worker
        assert len(threading.enumerate())==threads
        assert len(window.history_table.findChildren(ActivityCard))==1
    for query in ('record-1','record-2','none','')*5:
        window.search.setText(query); QTest.qWait(140)
        assert window.history_table.count()==len(window._history_rows)
        if window.history_table.count(): window.history_table.setCurrentCell(0,0)
        settle()
        assert len(window.history_table.findChildren(ActivityCard))<=1


def test_monitor_cycles_are_bounded_and_hidden_moves_continue(window,qapp,monkeypatch):
    fast_service(monkeypatch)
    for _ in range(10):
        window.service.configure(window.settings.folders,True)
        until(qapp,lambda:window._watching==2)
        window.service.configure(window.settings.folders,False)
        until(qapp,lambda:window._watching==0)
    window.hide()
    window.service.configure(window.settings.folders,True)
    until(qapp,lambda:window._watching==2)
    source=Path(window.selected_path)/'hidden-proof.pdf'; source.write_bytes(b'hidden proof')
    destination=source.parent/'Documents'/source.name
    until(qapp,lambda:destination.exists())
    assert destination.read_bytes()==b'hidden proof'
    until(qapp,lambda:any(h['destination']==str(destination) for h in window.store.load().history))


def test_watchdog_queue_capacity_is_bounded(window,qapp,monkeypatch):
    import fileflow.service as module
    original=module.Observer; observers=[]
    def create():
        observer=original(); observers.append(observer); return observer
    monkeypatch.setattr(module,'Observer',create)
    window.service.configure(window.settings.folders,True)
    until(qapp,lambda:window._watching==2)
    assert observers and observers[0].event_queue.maxsize==256
    window.service.configure(window.settings.folders,False)
    until(qapp,lambda:window._watching==0)
    assert not observers[0].is_alive()


def test_dirty_restore_preserves_selected_record_scroll_and_collapsed_details(window,qapp):
    fill(window)
    window.history_table.setCurrentCell(10,0); settle()
    selected=window.selected_event()
    card=window.activity_cards[0]; card.expand_button.setChecked(False); settle()
    window.history_table.verticalScrollBar().setValue(500); settle()
    scroll=window.history_table.verticalScrollBar().value()
    window.hide()
    window.on_activity(Activity(str(Path(window.selected_path)/'new-hidden.pdf'),status='success'))
    window.restore(); settle()
    assert window.selected_event()==selected
    assert window.history_table.verticalScrollBar().value()==scroll
    assert not window.activity_cards[0].expand_button.isChecked()


def test_completed_worker_does_not_retain_processed_activities(tmp_path,qapp,monkeypatch):
    import weakref
    from fileflow.models import Folder
    from fileflow.service import OrganizationService
    from PySide6.QtCore import QEventLoop,QTimer
    fast_service(monkeypatch)
    inbox=tmp_path/'Inbox'; inbox.mkdir()
    for n in range(100): (inbox/f'proof-{n}.pdf').write_bytes(str(n).encode())
    service=OrganizationService(); references=[]; done=[]
    errors=[]
    service.activity.connect(lambda activity: errors.append(activity.detail) if activity.status=='error' else None)
    service.activity.connect(lambda activity:references.append(weakref.ref(activity)))
    service.completed.connect(lambda *args:done.append(args))
    try:
        service.configure([Folder(str(inbox),True)],False); service.organize_now()
        loop=QEventLoop(); service.completed.connect(loop.quit)
        timeout=QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(20000)
        if not done: loop.exec()
        timeout.stop()
        assert done and len(references)==100 and not errors
        QTimer.singleShot(20,loop.quit); loop.exec()
        assert not any(reference() is not None for reference in references)
        assert len(list((inbox/'Documents').glob('*.pdf')))==100
    finally: service.shutdown()


def test_cleared_selection_keeps_retained_native_details_localized(window,qapp):
    fill(window); window.history_table.setCurrentCell(0,0); settle()
    card=window.activity_cards[0]
    window.history_table.clearSelection(); settle()
    assert window.selected_event() is None
    assert not card.property('selected')
    window.change_language(); settle()
    assert card.open_action.text()==window.t('open')
    from fileflow.visuals import timestamp
    assert card.timestamp_label.text()==timestamp(card.event['time'],window.settings.language)
    assert len(window.history_table.findChildren(ActivityCard))==1


def test_windows_memory_sampler_releases_temporary_buffers_without_cyclic_gc(window,qapp,monkeypatch):
    import ctypes,gc,os,weakref
    import pytest
    if os.name!='nt': pytest.skip('Windows memory APIs')
    from tools.profile_memory import measure
    original=ctypes.create_string_buffer; references=[]
    def track(*args,**kwargs):
        buffer=original(*args,**kwargs); references.append(weakref.ref(buffer)); return buffer
    monkeypatch.setattr(ctypes,'create_string_buffer',track)
    enabled=gc.isenabled(); gc.disable()
    try:
        for _ in range(3):
            result=measure(qapp,window)
            assert result['private_working_set_bytes']>0
        assert references and all(reference() is None for reference in references)
    finally:
        if enabled: gc.enable()
