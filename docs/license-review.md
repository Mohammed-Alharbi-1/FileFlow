# Distribution licensing review

The owner authorized publication while deferring the original-source license.
No MIT/GPL/Apache license is selected for original FileFlow code. The inactive
MIT draft is outside root LICENSE. LICENSING.md states the deferred status.

The chosen Qt distribution approach is LGPLv3 with a suitable shared-library
mechanism: external onedir DLL/PYD/plugin files, no library integrity lock,
express modification/reverse-engineering permission, installation/replacement
instructions, full LGPL/GPL text, upstream notices and complete corresponding
Qt Base/SVG/Image Formats/PySide/Shiboken 6.11.3 source archives inside the ZIP.
The archives retain build scripts and original copyrights. Source URLs/hashes
are pinned and checked by tools/prepare_compliance.py and package_public.py.
No Qt library modifications are made. Bundled plugin implementations inspected
in the corresponding sources offer LGPL; no GPL-only Qt application module is
included. Unused Mesa OpenGL is excluded rather than distributed without its
separate dependency/source review.

Python, watchdog, OpenSSL, libffi and bootloader notices are retained. The
PyInstaller exception permits distributing a bundled application subject to its
dependencies' terms. Microsoft runtime restrictions are preserved separately.
This is an engineering distribution review, not an assertion that the original
project is OSI-licensed or that a commercial Qt license has been purchased.

On 2026-10-29 the owner expressly confirmed the required rights to redistribute
the bundled Microsoft Visual C++ runtime DLLs. Their component restrictions
remain included in Python/LICENSE.txt and THIRD_PARTY_RIGHTS.md. This declaration
is separate from the deferred original-source license decision.
