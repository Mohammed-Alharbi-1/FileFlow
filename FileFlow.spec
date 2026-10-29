# Build on Windows: python -m PyInstaller --noconfirm --distpath dist/1.2.2 FileFlow.spec
from pathlib import Path
from importlib.metadata import distribution
import os
import sys

root = Path(SPECPATH)
# Isolate DLL discovery from unrelated tools on the host PATH (for example
# Poppler's incompatible icuuc.dll). Qt uses the Windows system ICU ABI.
if sys.platform == 'win32':
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    os.environ['PATH'] = os.pathsep.join((str(Path(sys.executable).parent),
                                         str(Path(sys.base_prefix)),
                                         str(windows / 'System32'), str(windows)))
notices = [(str(root / 'THIRD_PARTY_NOTICES.md'), '.')]
compliance = root / 'build' / 'compliance-portable'
assert (compliance / 'SOURCE_MANIFEST.json').is_file(), 'Run tools/prepare_compliance.py before building'
notices.append((str(compliance), 'licenses'))
for package in ('PySide6-Essentials', 'shiboken6', 'watchdog', 'pyinstaller'):
    dist = distribution(package)
    for entry in dist.files or []:
        if any(token in str(entry).lower() for token in ('license', 'copying', 'notice')):
            path = Path(dist.locate_file(entry))
            if path.is_file():
                notices.append((str(path), str(Path('licenses') / package / entry.parent)))
python_license = Path(__import__('sys').base_prefix) / 'LICENSE.txt'
if python_license.exists():
    notices.append((str(python_license), 'licenses/Python'))
analysis = Analysis(
    [str(root / 'main.py')], pathex=[str(root)],
    binaries=[], datas=notices,
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6.QtWebEngineCore',
              'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
)
# Qt Widgets uses raster rendering. Do not ship the unused Mesa software OpenGL
# implementation; its additional dependency/source set is outside this package.
analysis.binaries = [entry for entry in analysis.binaries
                     if Path(entry[0]).name.lower() != 'opengl32sw.dll']
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True, name='FileFlow',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'fileflow.ico'),
    version=str(root / 'version_info.txt'),
)
collection = COLLECT(exe, analysis.binaries, analysis.datas,
                     strip=False, upx=False, name='FileFlow')
