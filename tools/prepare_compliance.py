"""Fetch pinned, unmodified corresponding sources and preserve upstream notices.

Only run during packaging. No application runtime network access is introduced.
"""
import argparse
import hashlib
import json
import re
import shutil
import tarfile
from pathlib import Path
from urllib.request import urlretrieve

QT_BASE = 'https://download.qt.io/official_releases/'
SOURCES = [
    ('qtbase-everywhere-src-6.11.3.tar.xz', QT_BASE+'qt/6.11/6.11.3/submodules/', '46de0710b594945a5d446ae44354daa386141c6903c53781b2ca547bc62f8f8f'),
    ('qtsvg-everywhere-src-6.11.3.tar.xz', QT_BASE+'qt/6.11/6.11.3/submodules/', '9bdf6fa4b5a2d91c3eaa2edd12263fdff0ae19d0ac25d3c99946cd4189a07123'),
    ('qtimageformats-everywhere-src-6.11.3.tar.xz', QT_BASE+'qt/6.11/6.11.3/submodules/', '2759929c7abbc5376120394d1ccac1abbb816bc2791b34ece6c1412d323e6213'),
    ('pyside-setup-everywhere-src-6.11.3.tar.xz', QT_BASE+'QtForPython/pyside6/PySide6-6.11.3-src/', '050819cb05e14d6689f42b56e4fa9c8ff63be2bb339e0c094c45b990b7cabde1'),
]
NOTICES = [
    ('OpenSSL-LICENSE.txt', 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.8/LICENSE.txt', '7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a'),
    ('OpenSSL-AUTHORS.md', 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.8/AUTHORS.md', 'b9f638dfc06b59c2d3b808186c3b30f713805a5db390f5b77b1703ac58acb83e'),
    ('OpenSSL-README.md', 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.8/README.md', 'f68c351048c11bd8499b9d6ef8b283386d4544cc556fd2679a2ff2b1c50a378b'),
    ('libffi-LICENSE.txt', 'https://raw.githubusercontent.com/libffi/libffi/v3.4.6/LICENSE', '67894089811f93fca47a76f85e017da6f8582d4ba0905963c6e0f1ad6df7a195'),
]


def prepare(cache: Path, output: Path):
    cache.mkdir(parents=True, exist_ok=True)
    sources = output/'sources'
    sources.mkdir(parents=True, exist_ok=True)
    manifest = []
    notice_index = {}
    for name, base, expected in SOURCES:
        path = cache/name
        if not path.exists():
            urlretrieve(base+name, path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
        shutil.copyfile(path, sources/name)
        copyrights = set()
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                relative = Path(member.name)
                assert not relative.is_absolute() and '..' not in relative.parts
                # Readable license/attribution copies accompany the full archives.
                keep = ('LICENSES' in relative.parts or
                        re.search(r'(?i)license|copying|copyright|notice|qt_attribution', relative.name))
                if keep:
                    # Keep portable paths short even when the checkout is deep
                    # on Windows; original source paths remain in the index.
                    component = relative.parts[0].split('-everywhere')[0]
                    short = hashlib.sha256(member.name.encode()).hexdigest()[:12]+'-'+relative.name[:60]
                    target = output/'upstream-notices'/component/short
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
                    notice_index[target.relative_to(output).as_posix()] = member.name
                elif member.size < 2_000_000:
                    data = archive.extractfile(member).read()
                    if b'\0' not in data[:4096]:
                        for line in data.decode('utf-8', errors='replace').splitlines():
                            if re.search(r'(?i)copyright|SPDX-FileCopyrightText', line):
                                copyrights.add(line.strip())
        (output/(name+'.copyrights.txt')).write_text('\n'.join(sorted(copyrights))+'\n', encoding='utf-8')
        manifest.append(dict(file=name, url=base+name, sha256=expected))
        print('Preserved source and notices:', name, flush=True)
    (output/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    (output/'NOTICE_INDEX.json').write_text(json.dumps(notice_index, indent=2)+'\n', encoding='utf-8')
    for name, url, expected in NOTICES:
        path = cache/name
        if not path.exists():
            urlretrieve(url, path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
        shutil.copyfile(path, output/name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=Path('.test-artifacts/source-cache'))
    parser.add_argument('--output', type=Path, default=Path('build/compliance-portable'))
    args = parser.parse_args()
    prepare(args.cache, args.output)
