"""Read-only audit of input sources; writes evidence only into this directory."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = next(p for p in [ROOT / 'Pokemon-arena-d1882c0f-pokemon' / 'battery-sim', ROOT / 'battery-sim']
           if (p / 'src/sim.rs').is_file())
BIN = next((p for p in [SRC / 'target/release/battery-sim.exe', SRC / 'target/release/battery-sim']
            if p.is_file()), SRC / 'target/release/battery-sim.exe')


def main():
    evidence = {'csv': {}, 'runs': []}
    remote_path = HERE / 'github-tree.json'
    if remote_path.exists():
        remote = json.loads(remote_path.read_text(encoding='utf-8'))
        mismatch = []
        for item in remote:
            data = (SRC / item['path']).read_bytes().replace(b'\r\n', b'\n')
            sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if sha != item['sha']:
                mismatch.append(item['path'])
        evidence['github_comparison'] = {'files': len(remote), 'mismatches': mismatch}
        if mismatch:
            raise SystemExit('Historical source mismatch. In a separate checkout restore battery-sim from '
                             '697a0150204047c6a59f2ede0b7156cf3db27735 before reproducing v0.1 evidence. '
                             'No historical evidence was overwritten. Changed: ' + ', '.join(mismatch))
    for base in [ROOT / 'battery-sim2', SRC, HERE / 'inputs']:
        for name in ['grid.csv', 'mega.csv', 'optim_winners.csv', 'marathon.csv']:
            path = base / name
            if not path.exists():
                continue
            lines = path.read_text(encoding='utf-8-sig').splitlines()
            start = next(i for i, s in enumerate(lines) if s.startswith('cathode,anode,'))
            rows = list(csv.DictReader(lines[start:]))
            passed = [r for r in rows if r.get('passed') == 'true']
            evidence['csv'][str(path.relative_to(ROOT))] = {
                'rows': len(rows), 'preamble_lines': start, 'passed': len(passed),
                'best_rates_passed': dict(Counter(r['c_best'] for r in passed)),
                'passed_t80_zero': sum(float(r['t80_min']) == 0 for r in passed),
                'example_pass_t80_zero': next((r for r in passed if float(r['t80_min']) == 0), None),
                'top_drx_2c': sorted([r for r in passed if r['cathode'] == 'DRX' and r['c_best'] == '2'], key=lambda r: -float(r['wh_kg']))[:1],
            }
    cases = [
        ('flagship', 'NMC811', 'SIC', 'GEL', 30, 1.1, 25, 2),
        ('drx_cold', 'DRX', 'SIC', 'GEL', 40, 1.02, -10, 2),
        ('drx_room', 'DRX', 'SIC', 'GEL', 40, 1.02, 25, 2),
        ('lfp_free', 'LFP', 'LIFREE', 'LP57', 35, 1.02, 25, 2),
        ('nmc_free', 'NMC811', 'LIFREE', 'GEL', 35, 1.02, -10, 2),
        ('baseline', 'NMC811', 'GRAPHITE', 'LP57', 20, 1.1, 25, 2),
    ]
    logs = []
    for label, cath, an, el, loading, np, temp, rate in cases:
        trace = HERE / f'{label}-trace.csv'
        args = [str(BIN), 'cell', '--cathode', cath, '--anode', an, '--electrolyte', el,
                '--loading', str(loading), '--np', str(np), '--temp', str(temp),
                '--c-rate', str(rate), '--cycles', '3000', '--abuse',
                '--trace-every', '1000', '--csv', str(trace)]
        run = subprocess.run(args, capture_output=True, encoding='utf-8', check=True, timeout=60)
        logs.append(f'CASE {label}\nCOMMAND {subprocess.list2cmdline(args)}\n{run.stdout}')
        with trace.open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        cap0 = loading * {'NMC811': 200*.96, 'DRX': 250*.95, 'LFP': 160*.95}[cath] / 1000
        efc = sum((float(r['soc_top']) - float(r['soc_end'])) * float(r['capacity_mAh_cm2']) / cap0 for r in rows)
        evidence['runs'].append({'label': label, 'cycles': len(rows), 'efc_from_discharge_trace': efc,
                                  'first_soc_top': rows[0]['soc_top'], 'first_soc_end': rows[0]['soc_end'],
                                  'last_li_inventory_before_final_degradation': rows[-1]['li_inv']})
    (HERE / 'runtime.txt').write_text('\n\n'.join(logs), encoding='utf-8')
    (HERE / 'evidence.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(evidence, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
