from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .models import Settings


def default_settings_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "FileFlow" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or default_settings_path()

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        # Invalid JSON is reported by the UI. Never silently replace it.
        with self.path.open(encoding="utf-8") as stream:
            return Settings.from_dict(json.load(stream))

    def save(self, settings: Settings):
        # Theme/tray clicks on first launch must not create any files.
        if not any(f.confirmed for f in settings.folders) and not self.path.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(settings.to_dict(), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
