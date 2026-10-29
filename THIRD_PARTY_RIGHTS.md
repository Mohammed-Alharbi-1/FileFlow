# Third-party library rights and replacement

FileFlow uses Qt, PySide6 and Shiboken6 6.11.3 under LGPL version 3, with
separately licensed third-party components. Copies of LGPLv3 and GPLv3, original
copyright notices, complete unmodified corresponding source archives (including
build scripts), and a SHA-256/source URL manifest accompany the Windows ZIP in
_internal/licenses. The archives contain Qt Base, Qt SVG, Qt Image Formats and
PySide/Shiboken sources. No modifications to those libraries are made.

You are expressly permitted to modify the portions of FileFlow that use the
LGPL libraries for your own use, and to reverse engineer the combined work for
debugging such modifications. You may replace or relink the LGPL libraries and
run the resulting combined work with compatible modified versions. No term in
FileFlow's licensing status restricts those LGPL rights. This limited permission
does not grant a general software license for the original FileFlow source.

To replace libraries, quit FileFlow, back up the extracted portable folder and
build compatible Windows x64 Python 3.12/CPython abi3 libraries using the supplied
source archives and their CMake/README build instructions. Keep the same Qt 6.11
ABI and matching PySide/Shiboken build. Replace the corresponding DLLs/PYD files
in _internal/PySide6 and _internal/shiboken6 and plugins in the existing plugin
subdirectories. Start FileFlow.exe normally. The onedir executable loads these
external shared libraries; it has no hash, signature, activation-key or DRM check
on them. No installation key or special signing information is needed. Testing
modified libraries should use an isolated folder rather than personal files.
Qt plugins and their dependent DLLs must be replaced as a compatible set.

Source archives can be unpacked with a tar/xz-capable archive utility or Python's
tarfile module. Exact upstream download locations and hashes appear in
_internal/licenses/SOURCE_MANIFEST.json. They are also included directly, so
access to upstream servers is not required to obtain the supplied sources.

Python, watchdog, OpenSSL, libffi, and the PyInstaller bootloader retain their
respective notices and permissions. Microsoft runtime DLLs are Microsoft
Distributable Code and remain subject to their redistribution restrictions,
including those preserved in _internal/licenses/Python/LICENSE.txt. Those DLLs
are for supported Microsoft platforms, must not have their notices altered, and
must not be used in malicious/deceptive/unlawful software or in a manner implying
Microsoft endorsement. These component terms do not restrict LGPL library rights.
