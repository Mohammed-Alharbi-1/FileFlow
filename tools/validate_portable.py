"""Validate a portable build with bounded waits; never terminate the child."""
import argparse,json,subprocess,tempfile,sys,os,tomllib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fileflow import __version__
def validate(bundle,headless=False):
    project=tomllib.loads((Path(__file__).resolve().parents[1]/'pyproject.toml').read_text(encoding='utf-8'))
    assert project['project']['version']==__version__
    bundle=Path(bundle).resolve();exe=bundle/'FileFlow.exe'
    assert exe.is_file() and (bundle/'_internal').is_dir()
    assert (bundle/'_internal/licenses').is_dir()
    # Windows version resources are checked independently of Python metadata.
    command="$v=(Get-Item -LiteralPath '"+str(exe).replace("'","''")+"').VersionInfo; $v.FileVersion+'|'+$v.ProductVersion"
    version=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True).strip()
    assert version==__version__+'|'+__version__,(version,__version__)
    with tempfile.TemporaryDirectory(prefix='FileFlow-portable-check-') as temporary:
        report=Path(temporary)/'smoke.json'
        env=dict(os.environ)
        if headless:env['QT_QPA_PLATFORM']='offscreen'
        process=subprocess.Popen([str(exe),'--smoke-test',str(report)],env=env)
        assert process.wait(timeout=30)==0
        assert json.loads(report.read_text())['ok']
    print('Portable dependencies, version and real smoke test passed')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bundle');parser.add_argument('--headless',action='store_true');args=parser.parse_args();validate(args.bundle,args.headless)
