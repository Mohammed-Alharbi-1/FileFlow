# FileFlow 1.2.2 — Lightweight Windows File Organizer

A local Windows desktop file organizer with automatic folder monitoring,
custom extension/filename rules, Arabic and English, Light and Dark modes,
a modern desktop interface and a searchable activity history.

Version 1.2.2 reduces History widget allocations, defers hidden visual work and
improves responsiveness while preserving safe monitoring and reliable shutdown.
No cloud, accounts, server or Python installation is needed for the portable ZIP.

## Install

1. Download FileFlow-v1.2.2-windows-x64.zip and SHA256SUMS.txt.
2. Compare the ZIP's SHA-256 with the published checksum.
3. Extract the entire archive, including _internal and its licensing materials.
4. Open FileFlow.exe.
5. Add a folder and confirm its setup.
6. Configure rules and start organizing sample files.

Close-to-tray keeps monitoring active when enabled. Use Quit in the tray menu to
exit safely. FileFlow avoids silent overwrites, waits for stable files, ignores
temporary downloads and does not rearrange nested folders. Keep your backups:
there is no automatic undo or recovery bin.

The binary is unsigned; Windows may show security warnings. Windows 11 x64 was
tested locally. Windows 10 and multi-day resource stability remain unverified.
Resource usage depends on workload; historical measurements are not guarantees.

The original source license is deferred: no general software license is granted.
Third-party licenses and LGPL replacement/reverse-engineering rights are retained.
The ZIP includes complete corresponding Qt/PySide/Shiboken sources and notices.
Read LICENSING.md, THIRD_PARTY_NOTICES.md and THIRD_PARTY_RIGHTS.md in the package.
