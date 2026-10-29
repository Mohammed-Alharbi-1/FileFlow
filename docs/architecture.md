# Architecture

`main.py` / `fileflow/app.py` own startup and the configuration-scoped Windows
mutex. `ui.py`, `workspace.py` and `refinement.py` coordinate the existing native
window. `history_view.py` provides a list model/delegate and one lazy detail card.
`visuals.py` / `controls.py` provide original icons and native animated controls.
`service.py` owns one serialized non-daemon worker and watchdog observers with
bounded raw-event queues. `engine.py` owns stability checks and collision-safe
moves; `models.py` validates rules/routes and `storage.py` persists JSON atomically.

Hidden activity updates bounded History and defers view refresh, not monitoring.
Shutdown rejects jobs, cancels pending waits, drains active safe operations, stops
observers, polls worker termination without indefinitely joining on the GUI,
disposes tray resources and explicitly exits Qt. The engine is unchanged by
repository preparation. No web runtime or external backend is involved.
