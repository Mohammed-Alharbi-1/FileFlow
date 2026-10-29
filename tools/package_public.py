"""Create a complete portable ZIP and checksum, excluding local research logs."""
import argparse,hashlib,zipfile,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fileflow import __version__
parser=argparse.ArgumentParser();parser.add_argument('bundle',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--owner-review',action='store_true');args=parser.parse_args()
assert (args.bundle/'FileFlow.exe').is_file() and (args.bundle/'_internal').is_dir()
assert (args.bundle/'LICENSING.md').is_file(), 'Include the deferred source-license statement'
assert (args.bundle/'THIRD_PARTY_RIGHTS.md').is_file(), 'Preserve LGPL replacement/reverse engineering rights'
assert (args.bundle/'_internal/licenses/SOURCE_MANIFEST.json').is_file(), 'Include exact corresponding source information'
from tools.prepare_compliance import SOURCES
for name, _, checksum in SOURCES:
    source=args.bundle/'_internal/licenses/sources'/name
    assert source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()==checksum, name
assert list((args.bundle/'_internal/licenses').rglob('*LGPL-3.0-only.txt'))
assert list((args.bundle/'_internal/licenses').rglob('*GPL-3.0-only.txt'))
args.output.mkdir(parents=True,exist_ok=True)
archive=args.output/f'FileFlow-v{__version__}-windows-x64.zip'
assert not archive.exists(),'Never overwrite a previously prepared release asset'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(args.bundle.rglob('*')):
        if path.is_file():z.write(path,Path('FileFlow')/path.relative_to(args.bundle))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
(args.output/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='ascii')
shutil.copyfile(Path('docs')/f'release-notes-v{__version__}.md',args.output/'RELEASE_NOTES.md')
print(archive)
