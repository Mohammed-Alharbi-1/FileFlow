"""Exercise only verified isolated memory-test inboxes during sustained runs."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fileflow.models import validate_root

report=[]; pending=[]
temp_root=Path(tempfile.gettempdir()).resolve()
for root in temp_root.glob('FileFlow-memory-*'):
    if len(sys.argv)>2 and root.name!=sys.argv[2]: continue
    config=root/'Config/settings.json'
    if not config.is_file(): continue
    settings=json.loads(config.read_text(encoding='utf-8'))
    expected=[str(root/f'Inbox{n}') for n in range(3)]
    if [f['path'] for f in settings.get('folders',[])]!=expected or not settings.get('automatic'): continue
    assert root.resolve().parent==temp_root
    inbox=validate_root(root/'Inbox0'); assert inbox.is_relative_to(root.resolve())
    documents=inbox/'Documents'; documents.mkdir(exist_ok=True); validate_root(documents)
    filename=f'runtime-proof-{uuid.uuid4().hex}.txt'
    prior=documents/filename; source=inbox/filename; destination=documents/f'{source.stem} (1).txt'
    with prior.open('xb') as stream: stream.write(b'preserve original destination')
    with source.open('xb') as stream: stream.write(b'new isolated background source')
    pending.append((root,source,prior,destination))
deadline=time.monotonic()+15
for root,source,prior,destination in pending:
    while not destination.exists() and time.monotonic()<deadline:time.sleep(.02)
    assert destination.read_bytes()==b'new isolated background source'
    assert prior.read_bytes()==b'preserve original destination' and not source.exists()
    record=dict(fixture=root.name,success=True,collision_safe=True,
                destination_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    report.append(record)
assert report,'No verified isolated running memory fixtures found'
Path(sys.argv[1]).write_text(json.dumps(report,indent=2))
