"""Explicit publication allowlist/export and conservative static privacy checks."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES=['README.md','LICENSING.md','THIRD_PARTY_RIGHTS.md','CHANGELOG.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','SECURITY.md','THIRD_PARTY_NOTICES.md','.gitignore','.gitattributes','pyproject.toml','requirements.txt','requirements-dev.txt','FileFlow.spec','build.ps1','main.py','version_info.txt','GITHUB_RELEASE_CHECKLIST.md','GITHUB_PREPARATION_REPORT.md','GITHUB_PUBLICATION_REPORT.md']
def candidates():
    files=[ROOT/p for p in ROOT_FILES if (ROOT/p).is_file()]
    for folder in ['fileflow','tests','tools','.github','assets']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    files.extend((ROOT/'docs').glob('*.md'))
    files.extend((ROOT/'docs/license-drafts').glob('*.txt'))
    files.extend((ROOT/'docs/screenshots/public').glob('*.png'))
    return sorted(set(files))
def audit(files):
    findings=[]
    patterns=[r'(?i)[a-z]:[\\/]Users[\\/]',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'AKIA[0-9A-Z]{16}',r'sk-[A-Za-z0-9]{30,}']
    for path in files:
        if path.suffix.lower() in ('.png','.ico'):continue
        text=path.read_text(encoding='utf-8-sig')
        for pattern in patterns:
            if re.search(pattern,text):findings.append(str(path.relative_to(ROOT)))
    return sorted(set(findings))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    files=candidates();findings=audit(files)
    result={'candidate_files':len(files),'findings':findings,'method':'allowlist plus static private-path/common credential-pattern scan; not a guarantee against every secret'}
    if args.report:args.report.write_text(json.dumps(result,indent=2))
    assert not findings,findings
    if args.export:
        assert not args.export.exists(),'Export directory already exists'
        for path in files:
            target=args.export/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    print(json.dumps(result))
if __name__=='__main__':main()
