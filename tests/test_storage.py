import json

import pytest

from fileflow.models import Folder, Rule, Settings
from fileflow.storage import SettingsStore


def test_first_launch_has_no_filesystem_writes(tmp_path):
    store = SettingsStore(tmp_path / "not-created" / "settings.json")
    settings = store.load()
    settings.theme = "dark"
    store.save(settings)
    assert list(tmp_path.iterdir()) == []


def test_round_trip_after_explicit_setup(tmp_path):
    store = SettingsStore(tmp_path / "config" / "settings.json")
    folder = Folder(str(tmp_path), True, rules=[Rule("contains", "فاتورة", "الفواتير")])
    settings = Settings([folder], automatic=True, language="ar")
    store.save(settings)
    assert store.load() == settings
    assert list(store.path.parent.iterdir()) == [store.path]


def test_corrupt_settings_not_replaced(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(ValueError):
        SettingsStore(path).load()
    assert path.read_text() == "broken"


def test_untrusted_config_cannot_escape_folder(tmp_path):
    data = Settings([Folder(str(tmp_path), True)]).to_dict()
    data["folders"][0]["destinations"]["Images"] = "../../escape"
    with pytest.raises(ValueError):
        Settings.from_dict(data)


def test_overlapping_folders_rejected(tmp_path):
    data = Settings([Folder(str(tmp_path), True), Folder(str(tmp_path / "nested"), True)]).to_dict()
    with pytest.raises(ValueError):
        Settings.from_dict(data)


@pytest.mark.parametrize("value", [None, 23, ["bad"], {"nested": "bad"}])
def test_non_string_destination_is_rejected(tmp_path, value):
    data = Settings([Folder(str(tmp_path), True)]).to_dict()
    data["folders"][0]["destinations"]["Images"] = value
    with pytest.raises(ValueError):
        Settings.from_dict(data)


@pytest.mark.parametrize("field,value", [("value", 4), ("enabled", "false"), ("destination", None)])
def test_malformed_rule_is_rejected(tmp_path, field, value):
    data = Settings([Folder(str(tmp_path), True, rules=[Rule("extension", "txt", "Notes")])]).to_dict()
    data["folders"][0]["rules"][0][field] = value
    with pytest.raises(ValueError):
        Settings.from_dict(data)


def test_os_errors_with_filename_braces_are_literal():
    from fileflow.i18n import tr
    message = "Permission denied: invoice{2026}.txt"
    assert tr(message) == message
