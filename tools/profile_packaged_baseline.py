"""Read-only Windows memory sampling of the unchanged 1.2.1 executable.

Uses its existing isolated lifecycle diagnostic to exit cooperatively.
"""
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fileflow.models import Settings,Folder,Rule
from fileflow.storage import SettingsStore

kernel=ctypes.WinDLL('kernel32'); psapi=ctypes.WinDLL('psapi'); user=ctypes.WinDLL('user32')
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
kernel.CloseHandle.argtypes=[wintypes.HANDLE]
psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
psapi.QueryWorkingSet.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user.IsWindowVisible.argtypes=[wintypes.HWND]; user.IsWindowVisible.restype=wintypes.BOOL


def memory(pid):
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle: raise ctypes.WinError()
    try:
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak_ws','ws','peak_pool','pool','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
        counter=Counters(); counter.cb=ctypes.sizeof(counter)
        assert psapi.GetProcessMemoryInfo(handle,ctypes.byref(counter),counter.cb)
        result=dict(private_bytes=counter.private,working_set_bytes=counter.ws)
        buffer=ctypes.create_string_buffer(16<<20)
        if psapi.QueryWorkingSet(handle,buffer,len(buffer)):
            words=(ctypes.c_size_t*(len(buffer)//ctypes.sizeof(ctypes.c_size_t))).from_buffer(buffer)
            result['private_working_set_bytes']=sum(not(words[i+1]&(1<<8)) for i in range(words[0]))*4096
        return result
    finally: kernel.CloseHandle(handle)


def close_window(pid):
    found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    def visit(hwnd,param):
        owner=wintypes.DWORD(); user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid:
            title=ctypes.create_unicode_buffer(256); user.GetWindowTextW(hwnd,title,256)
            if title.value=='FileFlow':
                found.append(hwnd); user.PostMessageW(hwnd,0x10,0,0)
        return True
    callback=callback_type(visit); user.EnumWindows(callback,0)
    assert found, 'Native main window not found'
    return found[0]


def main():
    exe=Path(sys.argv[1]).absolute(); output=Path(sys.argv[2]); report=[]
    for count in (0,200):
        for automatic in (False,True):
            with tempfile.TemporaryDirectory(prefix='FileFlow-exe-baseline-') as temporary:
                root=Path(temporary); (root/'FILEFLOW_ISOLATED_TEST').touch(); inbox=root/'Inbox'; inbox.mkdir()
                settings=Settings([Folder(str(inbox),True,rules=[Rule('contains',f'match{n}',f'Route{n}') for n in range(6)])],automatic=automatic,tray=True)
                settings.history=[dict(source=str(inbox/f'file-{n}.pdf'),destination=str(inbox/'Documents'/f'file-{n}.pdf'),status='success',detail='',time='2026-10-28T08:00:00+03:00') for n in range(count)]
                store=SettingsStore(root/'Config/settings.json'); store.save(settings)
                child=root/'child.json'
                process=subprocess.Popen([str(exe),'--data-dir',str(store.path.parent),'--lifecycle-test',str(child),'--lifecycle-scenario','hold'])
                deadline=time.monotonic()+8
                while not child.exists() and process.poll() is None and time.monotonic()<deadline: time.sleep(.02)
                assert child.exists()
                time.sleep(.3); row=dict(history=count,automatic=automatic,pid=process.pid,visible=memory(process.pid))
                hwnd=close_window(process.pid); time.sleep(.3)
                row['window_hidden']=not bool(user.IsWindowVisible(hwnd)); assert row['window_hidden']
                row['hidden']=memory(process.pid)
                code=process.wait(timeout=15); assert code==0
                row['exit_code']=code; report.append(row); output.write_text(json.dumps(report,indent=2))

if __name__=='__main__': main()
