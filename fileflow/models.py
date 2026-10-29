from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PureWindowsPath
import os
import re
import uuid

CATEGORIES = {
    "Images": ("jpg", "jpeg", "png", "gif", "webp", "svg"),
    "Documents": ("pdf", "doc", "docx", "txt", "xlsx", "pptx", "csv"),
    "Videos": ("mp4", "mov", "avi", "mkv"),
    "Audio": ("mp3", "wav", "flac", "m4a"),
    "Archives": ("zip", "rar", "7z"),
    "Installers": ("exe", "msi", "msix"),
    "Other Files": (),
}
TEMP_EXTENSIONS = {".crdownload", ".part", ".tmp", ".partial", ".download"}
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.I)


def validate_destination(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("destination")
    value = value.strip().replace("\\", "/")
    parts = value.split("/")
    if (not value or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive
            or any(p in ("", ".", "..") for p in parts)):
        raise ValueError("destination")
    for part in parts:
        if (any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                or part.endswith((" ", ".")) or RESERVED.match(part)):
            raise ValueError("destination")
    return "/".join(parts)


def is_reparse(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def validate_root(path: str | Path) -> Path:
    root = Path(path).absolute()
    # Reject junctions/symlinks in all ancestors, including the selected root.
    for item in (root, *root.parents):
        if is_reparse(item):
            raise ValueError("symlink")
    if not root.is_dir():
        raise ValueError("folder")
    return root.resolve()


@dataclass
class Rule:
    kind: str = "extension"
    value: str = ""
    destination: str = "Documents"
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def validate(self):
        if (not all(isinstance(value, str) for value in (self.kind, self.value, self.destination, self.id))
                or not isinstance(self.enabled, bool)):
            raise ValueError("rule")
        if self.kind not in ("extension", "contains") or not self.value.strip():
            raise ValueError("rule")
        if self.kind == "extension" and any(c in self.value.lstrip(".") for c in '/\\:*?<>|. '):
            raise ValueError("rule")
        if self.kind == "extension" and not self.value.lstrip("."):
            raise ValueError("rule")
        validate_destination(self.destination)

    def matches(self, path: Path) -> bool:
        if not self.enabled:
            return False
        if self.kind == "extension":
            return path.suffix.casefold().lstrip(".") == self.value.strip().casefold().lstrip(".")
        return self.value.strip().casefold() in path.name.casefold()


@dataclass
class Folder:
    path: str
    confirmed: bool = False
    destinations: dict[str, str] = field(default_factory=lambda: {k: k for k in CATEGORIES})
    rules: list[Rule] = field(default_factory=list)

    def destination_for(self, path: Path) -> str:
        for rule in self.rules:
            if rule.matches(path):
                return validate_destination(rule.destination)
        extension = path.suffix.lower().lstrip(".")
        category = next((k for k, extensions in CATEGORIES.items() if extension in extensions), "Other Files")
        return validate_destination(self.destinations[category])

    def validate(self):
        if (not isinstance(self.path, str) or not Path(self.path).is_absolute()
                or not isinstance(self.confirmed, bool) or not isinstance(self.destinations, dict)
                or not isinstance(self.rules, list)):
            raise ValueError("folder")
        if set(self.destinations) != set(CATEGORIES):
            raise ValueError("destination")
        for value in self.destinations.values():
            validate_destination(value)
        for rule in self.rules:
            rule.validate()


@dataclass
class Settings:
    folders: list[Folder] = field(default_factory=list)
    automatic: bool = False
    theme: str = "light"
    language: str = "ar"
    tray: bool = False
    history: list[dict] = field(default_factory=list)

    def to_dict(self):
        return {"version": 1, **asdict(self)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("settings")
        settings = cls()
        for raw in data.get("folders", []):
            folder = Folder(path=raw["path"], confirmed=raw.get("confirmed") is True,
                            destinations=raw["destinations"],
                            rules=[Rule(**r) for r in raw.get("rules", [])])
            folder.validate()
            root = Path(folder.path)
            for existing in settings.folders:
                other = Path(existing.path)
                if root == other or root in other.parents or other in root.parents:
                    raise ValueError("overlap")
            settings.folders.append(folder)
        settings.automatic = data.get("automatic") is True
        settings.tray = data.get("tray") is True
        settings.theme = data.get("theme") if data.get("theme") in ("light", "dark") else "light"
        settings.language = "en" if data.get("language") == "en" else "ar"
        settings.history = [h for h in data.get("history", []) if isinstance(h, dict)
                            and all(isinstance(h.get(k), str) for k in ("source", "destination", "status", "detail", "time"))][-200:]
        return settings
