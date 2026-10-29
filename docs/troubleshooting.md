# Troubleshooting

- Extract the entire portable ZIP if the EXE reports missing Qt/Python libraries.
- Locked files or permissions can defer/prevent moves; close the writer or review
  folder access. Never force-kill FileFlow during an active move.
- Close may intentionally hide to tray. Use Show to restore or Quit to exit.
- If shutdown is waiting on storage, allow it to finish and review diagnostics.
- Corrupt JSON is reported rather than silently replaced. Preserve your local
  settings before attempting recovery. Report bugs with synthetic paths/data.
- Do not post settings, History, raw diagnostic logs or private paths publicly.
- Desktop tray automation is unavailable on some hosted CI runners. CI's
  headless lifecycle checks are separate from manual native-tray verification.
