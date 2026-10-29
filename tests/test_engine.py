from pathlib import Path
from threading import Event, Thread
import os
import time

import pytest

from fileflow.engine import Organizer, protected_source, rename_no_replace, wait_stable
from fileflow.models import CATEGORIES, Folder, Rule, validate_destination


@pytest.fixture
def inbox(tmp_path):
    root = tmp_path / "Inbox"
    root.mkdir()
    return root


@pytest.fixture
def organizer():
    return Organizer(interval=.005, quiet=.015, timeout=.2)


def test_no_setup_no_changes(inbox, organizer):
    source = inbox / "hello.txt"
    source.write_bytes(b"original")
    assert organizer.organize(Folder(str(inbox))) == []
    assert list(inbox.iterdir()) == [source]


def test_application_state_directory_is_excluded(inbox):
    source = inbox / "settings.json"
    source.write_bytes(b"protected settings")
    organizer = Organizer(excluded_directories=[inbox])
    assert organizer.organize(Folder(str(inbox), True)) == []
    assert list(inbox.iterdir()) == [source]


@pytest.mark.parametrize("category,ext", [(c, ext) for c, exts in CATEGORIES.items() for ext in exts] + [("Other Files", "xyz"), ("Other Files", "")])
def test_all_file_types(inbox, organizer, category, ext):
    filename = "sample" + ("." + ext.upper() if ext else "")
    (inbox / filename).write_bytes(b"payload")
    activity = organizer.organize(Folder(str(inbox), True))
    assert activity[0].status == "success", activity
    assert (inbox / category / filename).read_bytes() == b"payload"
    assert not (inbox / filename).exists()


def test_numbered_collisions_preserve_every_file(inbox, organizer):
    destination = inbox / "Documents"
    destination.mkdir()
    (destination / "report.txt").write_bytes(b"first")
    (destination / "report (1).txt").write_bytes(b"second")
    (inbox / "report.txt").write_bytes(b"third")
    result = organizer.organize(Folder(str(inbox), True))
    assert result[0].status == "success", result
    assert (destination / "report.txt").read_bytes() == b"first"
    assert (destination / "report (1).txt").read_bytes() == b"second"
    assert (destination / "report (2).txt").read_bytes() == b"third"


def test_atomic_collision_refuses_existing_destination(inbox):
    source, target = inbox / "a.txt", inbox / "b.txt"
    source.write_bytes(b"a")
    target.write_bytes(b"b")
    with protected_source(source) as handle:
        with pytest.raises(FileExistsError):
            rename_no_replace(source, target, handle)
    assert source.read_bytes() == b"a"
    assert target.read_bytes() == b"b"


def test_nested_folders_and_temporary_downloads_untouched(inbox, organizer):
    nested = inbox / "Existing"
    nested.mkdir()
    (nested / "inside.txt").write_bytes(b"nested")
    names = ["one.crdownload", "two.part", "three.tmp", "~$report.docx", ".~lock.txt"]
    for name in names:
        (inbox / name).write_bytes(b"partial")
    assert organizer.organize(Folder(str(inbox), True)) == []
    assert all((inbox / name).exists() for name in names)
    assert (nested / "inside.txt").read_bytes() == b"nested"


def test_ordered_case_insensitive_rules_and_custom_destinations(inbox, organizer):
    folder = Folder(str(inbox), True)
    folder.destinations["Images"] = "Media/Photos"
    folder.rules = [Rule("contains", "invoice", "Disabled", False),
                    Rule("contains", "INVOICE", "Work/Bills"),
                    Rule("extension", ".PDF", "PDFs")]
    for name in ("invoice.pdf", "notes.PDF", "photo.png"):
        (inbox / name).write_bytes(name.encode())
    result = organizer.organize(folder)
    assert all(a.status == "success" for a in result), result
    assert (inbox / "Work/Bills/invoice.pdf").exists()
    assert (inbox / "PDFs/notes.PDF").exists()
    assert (inbox / "Media/Photos/photo.png").exists()
    assert not (inbox / "Disabled").exists()
    assert organizer.organize(folder) == []  # No recursive processing.


@pytest.mark.parametrize("value", ["", "..", "../outside", "C:/escape", "/absolute", "foo//bar", "foo/../bar", "CON", "com1.txt", "NUL", "bad?name", "end.", "path/ ", "foo:bar", "\\\\server\\share"])
def test_invalid_destination(value):
    with pytest.raises(ValueError):
        validate_destination(value)


def test_destination_file_conflict_preserves_source(inbox, organizer):
    (inbox / "Documents").write_bytes(b"obstacle")
    (inbox / "report.txt").write_bytes(b"source")
    result = organizer.organize(Folder(str(inbox), True))
    assert any(a.status == "error" for a in result)
    assert (inbox / "report.txt").read_bytes() == b"source"


def test_file_stability_waits_for_writer(inbox):
    source = inbox / "growing.txt"
    source.write_bytes(b"start")
    finished = Event()

    def writer():
        for _ in range(7):
            time.sleep(.015)
            with source.open("ab") as stream:
                stream.write(b"more")
                stream.flush()
        finished.set()

    thread = Thread(target=writer)
    thread.start()
    assert wait_stable(source, Event(), interval=.005, quiet=.04, timeout=1)
    assert finished.is_set()
    thread.join()


def test_unstable_file_is_deferred(inbox):
    source = inbox / "growing.txt"
    source.write_bytes(b"start")
    finish = Event()

    def writer():
        while not finish.wait(.005):
            with source.open("ab") as stream:
                stream.write(b"x")

    thread = Thread(target=writer)
    thread.start()
    try:
        result = Organizer(interval=.005, quiet=.04, timeout=.09).organize(Folder(str(inbox), True))
        assert result[0].status == "deferred"
        assert source.exists()
        assert not (inbox / "Documents").exists()
    finally:
        finish.set()
        thread.join()


def test_cancel_during_stability_does_not_move(inbox, organizer):
    source = inbox / "hello.txt"
    source.write_bytes(b"data")
    stop = Event()
    stop.set()
    assert organizer.organize(Folder(str(inbox), True), stop) == []
    assert source.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle sharing")
def test_open_writer_is_not_moved(inbox, organizer):
    source = inbox / "locked.txt"
    with source.open("wb") as writer:
        writer.write(b"still writing")
        writer.flush()
        result = organizer.organize(Folder(str(inbox), True))
        assert result[0].status == "error"
        assert source.exists()
    result = organizer.organize(Folder(str(inbox), True))
    assert result[0].status == "success"


def test_permission_error_preserves_source(inbox, organizer, monkeypatch):
    import fileflow.engine as engine
    source = inbox / "hello.txt"
    source.write_bytes(b"data")

    def denied(*_):
        raise PermissionError("denied")

    monkeypatch.setattr(engine, "rename_no_replace", denied)
    result = organizer.organize(Folder(str(inbox), True))
    assert result[0].status == "error"
    assert source.read_bytes() == b"data"


def test_unicode_paths_including_non_bmp(inbox, organizer):
    source = inbox / "فاتورة 🧾.txt"
    source.write_bytes(b"unicode")
    folder = Folder(str(inbox), True)
    folder.destinations["Documents"] = "مستنداتي 📁"
    result = organizer.organize(folder)
    assert result[0].status == "success", result
    assert (inbox / "مستنداتي 📁" / source.name).read_bytes() == b"unicode"


@pytest.mark.skipif(os.name != "nt", reason="Windows junction protection")
def test_junction_destination_rejected(inbox, tmp_path, organizer):
    import subprocess
    outside = tmp_path / "outside"
    outside.mkdir()
    junction = inbox / "Documents"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True)
    assert result.returncode == 0
    try:
        source = inbox / "secret.txt"
        source.write_bytes(b"safe")
        result = organizer.organize(Folder(str(inbox), True))
        assert result[0].status == "error"
        assert source.read_bytes() == b"safe"
        assert list(outside.iterdir()) == []
    finally:
        junction.rmdir()
