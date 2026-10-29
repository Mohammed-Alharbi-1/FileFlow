# Third-party notices

FileFlow uses Qt/PySide6/Shiboken6 6.11.3 under LGPLv3, with separately licensed
third-party components. The original FileFlow license remains deferred.
Read [LGPL rights and library replacement](THIRD_PARTY_RIGHTS.md).

| Component | Distribution terms | Included materials |
|---|---|---|
| Python 3.12.14 | PSF license and bundled component licenses | _internal/licenses/Python/LICENSE.txt |
| Qt Base 6.11.3 (Core, Gui, Widgets, Network, Test; platform/style/TLS/image plugins) | LGPLv3 and component terms | Complete source, LICENSES, copyright and attribution files |
| Qt SVG 6.11.3 (SVG plugins) | LGPLv3 and component terms | Complete source and notices |
| Qt Image Formats 6.11.3 (ICNS, TGA, TIFF, WBMP, WebP plugins) | LGPLv3 and component terms | Complete source and notices, including codec licenses |
| PySide6 Essentials / Shiboken6 6.11.3 | LGPLv3 | Complete pyside-setup source and notices |
| watchdog 6.0.0 | Apache-2.0 | Upstream LICENSE and COPYING |
| PyInstaller bootloader 6.22.3 | GPL with executable-distribution exception | Upstream COPYING.txt |
| OpenSSL 3.5.8 (Python libcrypto) | Apache-2.0 | OpenSSL-LICENSE.txt, AUTHORS and README |
| libffi (Python ctypes) | Permissive libffi license | libffi-LICENSE.txt |
| Microsoft Visual C++ runtime DLLs | Microsoft Distributable Code terms | Python/LICENSE.txt redistribution restrictions |

Qt third-party code includes codecs, compression, font/text, hashing and other
utilities under individual licenses. Readable upstream LICENSE/COPYING/NOTICE,
qt_attribution.json and copyright copies are preserved in
_internal/licenses/upstream-notices and *.copyrights.txt. The complete unmodified
source archives in _internal/licenses/sources also retain all original files and
notices. SOURCE_MANIFEST.json records exact upstream URLs and SHA-256 hashes.
GPL-only Qt application modules are not included. The unused Mesa software
OpenGL DLL is excluded; the application uses Qt Widgets raster rendering.

The portable folder must be distributed in full, including these materials.
Do not redistribute just FileFlow.exe. No proprietary Hazel/Noodlesoft or Apple
code, images, icons, branding or binaries are included.

Primary references:

- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
- [Qt for Python licenses](https://doc.qt.io/qtforpython-6/licenses.html)
- [Python license](https://docs.python.org/3/license.html)
- [watchdog license](https://github.com/gorakhargosh/watchdog/blob/master/LICENSE)
- [PyInstaller exception](https://pyinstaller.org/en/stable/license.html)
