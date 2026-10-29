# FileFlow 1.2.2 publication report

Verified on 2026-10-29. Status: **PUBLIC REPOSITORY AND WINDOWS RELEASE PUBLISHED**.

## Verified public links

- Repository: https://github.com/Mohammed-Alharbi-1/FileFlow
- Release: https://github.com/Mohammed-Alharbi-1/FileFlow/releases/tag/v1.2.2
- Windows ZIP: https://github.com/Mohammed-Alharbi-1/FileFlow/releases/download/v1.2.2/FileFlow-v1.2.2-windows-x64.zip
- Checksum: https://github.com/Mohammed-Alharbi-1/FileFlow/releases/download/v1.2.2/SHA256SUMS.txt
- Release revision CI: https://github.com/Mohammed-Alharbi-1/FileFlow/actions/runs/40809090539

Release source commit: `9b00885ad9681407a5ad8b2edc727d46e4e67530`.
Annotated tag: `v1.2.2`, verified locally and against the remote dereferenced tag.
The subsequent publication-record update changes documentation only; it does not
change the release tag, application source or validated binary.

Authenticated owner `Mohammed-Alharbi-1` was verified through the existing GitHub
CLI login and API, independently of the copyright attribution `M.Alharbi`.
A new private staging repository was created only after local gates passed.
The shared parent development workspace was not published or added as a remote.

## Validation

| Check | Actual result |
|---|---|
| Complete local source suite | 115 passed in 61.35 seconds |
| Hosted Windows / Python 3.12 CI | Success while repository was private |
| Hosted test selection | 114 passed, 1 native-desktop case deselected, 35.48 seconds |
| Hosted process lifecycle | 8 offscreen cases passed; no native-tray claim |
| Fresh native EXE lifecycle | 19 cases passed, including 10 tray cycles, background moves, active/pending shutdown, singleton and relaunch |
| Extracted final ZIP lifecycle | 10 native cases passed in an isolated temporary folder |
| EXE metadata / startup | FileVersion and ProductVersion 1.2.2; native smoke passed |
| Signature | NotSigned; no certificate or eliminated Windows warnings claimed |
| Theme / language switching | 200 transitions across empty and 200-record fixtures, three active watched folders |
| 200-record switch medians | Theme wall time 77.82 / 77.96 ms; language wall time 46.14 / 46.48 ms |
| Short hidden memory regression | 60.0 seconds; 302 widgets and 6 Python threads; sampled Private Bytes 51.055–51.395 MiB with profiling overhead |
| Restore responsiveness | Median 31.13 ms; maximum 35.34 ms in that fixture |
| ZIP integrity | CRC, extraction, runtime/source presence and SHA-256 passed |
| Actual public download | Downloaded without authentication and matched validated bytes |
| Public README | Rendered HTML, table, links and all four synthetic screenshots verified |
| Repository metadata | Public; requested description and eight topics verified |

All filesystem/monitoring checks used isolated temporary fixtures. No personal
Downloads, Desktop or Documents folders were organized. The original application
source is byte-identical to the previously validated implementation. Changes are
release tooling, distribution notices, packaging and documentation.

## Security and privacy

The release commit contains exactly 80 allowlisted files: no EXE/ZIP/DLL, virtual
environment, build output, user settings, History, raw logs or unrelated project.
The staged-file list was compared with the allowlist. Ignore rules were checked
against private/build/settings examples. A case-insensitive ignore collision
with bug_report.md was fixed before the initial commit.

Static private-path/common credential-pattern scan: zero findings. Frozen PYZ
inspection: 6,480 code objects checked, zero private build-path findings in the
checked filenames/string constants. Four public screenshots match the previously
reviewed synthetic fixtures. These scoped checks are not an exhaustive guarantee
against every secret or vulnerability. No authentication tokens appear here.

Workflow YAML parsed without duplicate-key errors. Official Actions revisions
were verified and pinned; workflows use read-only contents permissions. Future
release review requires explicit manual dispatch and compliance confirmation;
tag pushes cannot automatically create a competing release.

GitHub private vulnerability reporting was enabled and verified through the API.
Use the repository Security page for private reports; do not publish sensitive
file lists, credentials or exploit details in public issues.

## Distribution licensing

The original FileFlow source license remains **deferred**. No MIT/GPL/Apache or
other general project software license has been selected or granted. GitHub's
public license metadata is null. The inactive MIT proposal is outside active
root LICENSE, in docs/license-drafts. This is not represented as an OSI-licensed
open-source release.

Qt/PySide6/Shiboken6 6.11.3 use the LGPLv3 shared-library distribution approach:
external DLL/PYD/plugins, full LGPL/GPL texts, upstream notices/copyrights,
express modification/reverse-engineering permissions and replacement instructions.
Four complete unmodified source archives (Qt Base, Qt SVG, Qt Image Formats,
PySide/Shiboken), including build scripts, are included directly in the ZIP.
Their URLs and SHA-256 hashes are pinned, recorded and checked. Readable notices
use short portable paths with an original-path index. This fixes a Windows path
length failure found during the first fresh build; the failed candidate was not
published and no stable release was overwritten.

The shipped Qt module/plugin set was reviewed against corresponding sources;
GPL-only Qt application modules are not included. Unused Mesa software OpenGL
is excluded. An isolated changed QtCore DLL load probe passed (a compatible PE
overlay modification, not a claim that arbitrary ABI changes will work).

Python, watchdog, OpenSSL, libffi and PyInstaller bootloader notices are retained.
The PyInstaller executable-distribution exception was reviewed. The owner
expressly confirmed Microsoft Visual C++ runtime redistribution rights before
remote staging; applicable component restrictions remain included.

See LICENSING.md, THIRD_PARTY_NOTICES.md, THIRD_PARTY_RIGHTS.md and
_internal/licenses in the portable folder. Reference terms:
[Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations),
[Qt licensing](https://doc.qt.io/qt-6/licensing.html),
[PyInstaller exception](https://pyinstaller.org/en/stable/license.html),
[Microsoft redistribution](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170).

## Asset identity and publication sequence

Filename: `FileFlow-v1.2.2-windows-x64.zip`.
Size: 104,067,594 bytes. The full corresponding sources account for much of the
download; they are not loaded into the running application's memory.

SHA-256:

```text
ce4ba6a81d0860a2d87f8940275ba7c268485e6ebb60d445376e33a80c8586ee
```

Executable SHA-256:

```text
00cb59da17b0ed1db2ef0a06d9a725fb9661d5db3f303ac97e402dff371bad4a
```

The private draft's two assets, server digests, downloaded bytes, checksum file,
notes and tag were verified before public conversion. No hosted auto-generated
binary replaced the locally tested package. Release published at
2026-10-29T02:59:25Z.

Immediately after public conversion, the first release-publication API call
returned HTTP 404. The public-source/unpublished-release state was reported at
once. The existing draft and unchanged assets were rechecked; retry succeeded.
No public history was deleted or rewritten and no rollback of exposure is claimed.
Anonymous final checks then confirmed both source and release were public.

## Remaining limits

Windows 11 x64 was validated locally; Windows 10 and multi-day resource stability
remain unverified. The EXE is unsigned. Resource measurements are fixture/device
observations, not a universal RAM or responsiveness guarantee. There is no
automatic undo, backup, updater or startup registration. The original source
license is deferred, and the community Code of Conduct remains a proposal until
its separate adoption/enforcement arrangements are finalized.
