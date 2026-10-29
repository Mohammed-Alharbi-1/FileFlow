# Validation and measurement interpretation

Historical 1.2.2 evidence: 115 tests passed; source and packaged EXE each completed
1,800.015 seconds of native-event-loop hidden monitoring. Widgets stayed at 302
and Python threads at six. Corrected profiled EXE Private Bytes ranged
47.56–47.99 MiB; tracing/sampling overhead is included. Native tray Quit/relaunch
tests used actual child processes and preserved collision/stability safety.

A controlled untraced packaged comparison with one folder, six rules and 200
records measured hidden monitored Private Bytes 90.97 → 41.40 MiB and Private
Working Set 85.84 → 36.67 MiB. The historical source comparison used three folders
and 18 rules. These fixtures and metrics differ; do not interchange them or
interpret a user's single Task Manager reading as a universal benchmark.

Private Bytes measures private commit; Working Set includes shared resident
pages; Private Working Set excludes shareable resident pages and is the closest
provided comparison to Task Manager's ordinary process Memory column.

Raw historical logs are kept locally because they contain private machine paths.
Early profiler artifacts were corrected (long QtTest waits holding the GIL and
cyclic ctypes buffer views). Those aborted/artifact runs are excluded from the
30-minute claims. Native tray testing requires an interactive desktop; hosted
offscreen lifecycle tests deliberately do not claim native tray coverage.

Current publication checks and their actual results are recorded in
GITHUB_PREPARATION_REPORT.md. Windows 10 and multi-day stability remain untested.
