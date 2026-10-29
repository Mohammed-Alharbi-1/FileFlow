"""Native Windows process checks. Timeouts report failure; never kill a child.

Source: python tools/verify_lifecycle.py REPORT.json
Bundle: python tools/verify_lifecycle.py REPORT.json --exe dist/1.2.2/FileFlow/FileFlow.exe
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fileflow.models import Folder, Settings
from fileflow.storage import SettingsStore


def verify(report_path, exe=None, cycles=10, headless=False):
    report = dict(ok=False, cycles=cycles, packaged=bool(exe), cases=[])
    base = [str(Path(exe).absolute())] if exe else [sys.executable, str(Path(__file__).resolve().parents[1] / 'main.py')]
    env = dict(os.environ); env.pop('QT_QPA_PLATFORM', None); env['PYTHONUTF8'] = '1'
    if headless: env['QT_QPA_PLATFORM'] = 'offscreen'
    report['native_tray_tested'] = not headless
    temp_context = tempfile.TemporaryDirectory(prefix='FileFlow-lifecycle-')
    with temp_context as temp:
        root = Path(temp); (root / 'FILEFLOW_ISOLATED_TEST').touch(); (root / 'Inbox').mkdir()
        store = SettingsStore(root / 'Config/settings.json')
        def launch(scenario, label):
            if scenario != 'duplicate':
                store.save(Settings(folders=[Folder(str(root / 'Inbox'), True)], tray=scenario in ('tray','background'), automatic=scenario in ('background','monitoring','pending','active')))
            child_report = root / f'{label}.json'; log = root / f'{label}.jsonl'
            cmd = base + ['--data-dir', str(store.path.parent), '--lifecycle-test', str(child_report), '--lifecycle-scenario', 'hold' if scenario == 'duplicate' else scenario, '--diagnostics', str(log)]
            started = time.perf_counter()
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return process, child_report, log, started
        def collect(child, label, expected=0):
            process, child_report, log, started = child
            try: code = process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                # Preserve fixtures for an unresponsive process; no unsafe teardown.
                # TemporaryDirectory cleanup is disabled on this exceptional path.
                temporary_finalizer = getattr(temp_context, '_finalizer', None)
                if temporary_finalizer: temporary_finalizer.detach()
                temp_context.cleanup = lambda: None
                report['cases'].append(dict(label=label, pid=process.pid, terminated=False, timeout_s=25))
                report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
                raise RuntimeError(f'PID {process.pid} still alive after 25s; no kill attempted')
            result = dict(label=label, pid=process.pid, exit_code=code, elapsed_s=round(time.perf_counter()-started, 3), terminated=process.poll() is not None)
            result['child'] = json.loads(child_report.read_text(encoding='utf-8')) if child_report.exists() else {}
            result['diagnostics'] = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
            report['cases'].append(result)
            report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            assert code == expected, result
            if expected == 0:
                child_data = result['child']
                assert not child_data.get('rescue', True) and child_data.get('worker_finished') and child_data.get('shutdown') == 'complete', result
                assert child_data['threads'] == ['MainThread'], result
                assert any(event['event'] == 'mutex_released' for event in result['diagnostics']), result
            print(f'{label}: exit={code}, terminated=True, {result["elapsed_s"]}s', flush=True)
            return result['child']
        for index in range(0 if headless else cycles):
            result = collect(launch('tray', f'cycle-{index+1}'), f'cycle-{index+1}')
            assert result['tray_available'], 'Native tray unavailable; cannot claim tray coverage'
            hidden = next(e for e in result['events'] if e['event'] == 'close_to_tray')
            assert hidden['visible'] is False and hidden['state'] == 'running'
        for scenario in ('close','background','monitoring','pending','active'):
            if headless and scenario == 'background': continue
            source = root / 'Inbox/proof.txt'; destination = root / 'Inbox/Documents/proof.txt'
            if destination.exists(): destination.unlink()  # Isolated test fixture only.
            source.write_bytes(b'file safety proof')
            result = collect(launch(scenario, scenario), scenario)
            assert result['proof_preserved']
            names = [e['event'] for e in result['events']]
            if scenario == 'background': assert 'background_move' in names
            if scenario == 'monitoring': assert 'watching' in names
            if scenario == 'pending': assert 'pending_stability' in names and not result['proof_moved']
            if scenario == 'active': assert 'move_in_flight' in names and result['proof_moved']
            if scenario == 'active':
                saved = store.load()
                assert any(h['status']=='success' and h['destination'].endswith('proof.txt') for h in saved.history), 'Final move history was not persisted'
        first = launch('hold', 'singleton-owner')
        deadline = time.monotonic()+8
        while not first[1].exists() and time.monotonic()<deadline: time.sleep(.02)
        assert first[1].exists(), 'owner did not become ready'
        collect(launch('duplicate', 'singleton-duplicate'), 'singleton-duplicate', 17)
        collect(first, 'singleton-owner')
        collect(launch('startup-failure', 'startup-failure'), 'startup-failure', 19)
        collect(launch('close', 'after-startup-failure'), 'after-startup-failure')
        report['ok'] = True
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('report', type=Path); parser.add_argument('--exe', type=Path); parser.add_argument('--cycles', type=int, default=10); parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    verify(args.report, args.exe, args.cycles, args.headless)
