"""Reproduce post-audit cases without overwriting historical audit evidence."""
import argparse
import csv
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ('flagship', 'NMC811', 'SIC', 'GEL', 30, 1.1, 25),
    ('drx_cold', 'DRX', 'SIC', 'GEL', 40, 1.02, -10),
    ('drx_room', 'DRX', 'SIC', 'GEL', 40, 1.02, 25),
    ('lfp_free', 'LFP', 'LIFREE', 'LP57', 35, 1.02, 25),
    ('nmc_free', 'NMC811', 'LIFREE', 'GEL', 35, 1.02, -10),
    ('baseline', 'NMC811', 'GRAPHITE', 'LP57', 20, 1.1, 25),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sweep', action='store_true', help='Also run the historical 2880-design grid')
    args = parser.parse_args()
    binary = next((p for p in [ROOT / 'target/release/battery-sim.exe', ROOT / 'target/release/battery-sim'] if p.exists()), None)
    if binary is None:
        parser.error('Build first: cargo build --release')
    out = ROOT / 'results/v0.2.0'
    out.mkdir(parents=True, exist_ok=True)
    logs = []
    summaries = []

    def run(argv):
        proc = subprocess.run([str(binary)] + argv, capture_output=True, encoding='utf-8', check=True, timeout=600)
        logs.append('COMMAND battery-sim ' + subprocess.list2cmdline(argv) + '\n' + proc.stderr + proc.stdout)
        return proc.stdout

    for label, ca, an, el, ld, np, temp in CASES:
        trace = out / f'{label}-trace.csv'
        log = run(['cell', '--cathode', ca, '--anode', an, '--electrolyte', el,
                   '--loading', str(ld), '--np', str(np), '--temp', str(temp),
                   '--c-rate', '2', '--cycles', '3000', '--abuse', '--trace-every', '1000', '--csv', str(trace)])
        with trace.open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        for prev, cur in zip(rows, rows[1:]):
            assert abs(float(cur['soc_start']) - float(prev['soc_end'])) < 2e-6, label
        for row in rows:
            assert 0 <= float(row['soc_end']) <= 1, label
            assert 0 <= float(row['soc_top']) <= 1, label
            cap = float(row['capacity_mAh_cm2'])
            q = float(row['discharge_mAh_cm2'])
            expected = cap * (float(row['soc_top']) - float(row['soc_end']))
            assert abs(q - expected) < 2e-5, (label, row['cycle'])
        raw_cycles = int(re.search(r'EOL: .*? po (\d+) cyklach', log).group(1))
        energies = re.search(r'Energia oddana: ([\d.]+) Wh/kg .*?nominalna OCV: ([\d.]+)', log)
        qualifying = int(re.search(r'kwalifikowane cykle: (\d+)', log).group(1))
        summaries.append({
            'case': label, 'configuration': f'{ca}/{an}/{el}', 'temp_C': temp,
            'raw_cycles': raw_cycles, 'qualifying_cycles': qualifying,
            'nominal_wh_kg': float(energies.group(2)), 'delivered_wh_kg_first': float(energies.group(1)),
            'first_discharge_fraction': float(rows[0]['soc_top']) - float(rows[0]['soc_end']),
            't10_80_min_first': float(rows[0]['t10_80_min']) if rows[0]['t10_80_min'] else None,
            'efc': float(rows[-1]['efc']), 'physical_validation': 'unvalidated',
        })
    result = {'version': '0.2.0', 'protocol': 'CC 2C/1C, fixed current referenced to initial Ah; no CV',
              'qualification': '>=80% remaining capacity delivered; 10-80% <=30 min', 'cases': summaries}
    if args.sweep:
        sweep_path = out / 'optim_winners_v02.csv'
        run(['sweep', '--cathodes', 'NMC811,LFP,DRX', '--anodes', 'LIFREE,SIC,GRAPHITE',
             '--electrolytes', 'LP57,GEL,IONIC,SOLID', '--loadings', '20,25,30,35',
             '--nps', '1.02,1.05,1.1,1.2', '--temps', '-10,0,10,25,45', '--c-rates', '2,3',
             '--csv', str(sweep_path), '--top', '12'])
        with sweep_path.open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2880
        assert all(r['model_version'] == '0.2.0' for r in rows)
        assert all(r['passed'] == 'false' for r in rows), 'Unmodeled overcharge cannot pass'
        performance = [r for r in rows if r['performance_pass'] == 'true']
        assert all(float(r['t10_80_min']) <= 30 and int(r['qualifying_cycles']) >= 500 and float(r['c_best']) >= 2 for r in performance)
        result['sweep'] = {'rows': len(rows), 'performance_pass': len(performance), 'full_model_pass': 0,
                           'performance_by_cathode': dict(Counter(r['cathode'] for r in performance)),
                           'performance_missing_t10_80': sum(not r['t10_80_min'] for r in performance)}
    run(['report', '--lang', 'en', '--out', str(out / 'report-en.md')])
    run(['report', '--lang', 'pl', '--out', str(out / 'report-pl.md')])
    (out / 'summary.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    (out / 'runtime.txt').write_text('\n\n'.join(logs), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
