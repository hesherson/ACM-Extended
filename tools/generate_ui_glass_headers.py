#!/usr/bin/env python3
"""Reproduce the static decorative frame pools. Does not rewrite native UI definitions."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'tools/ui-glass-surfaces.json').read_text())
    for dialog in manifest['dialogs']:
        expected='// Generated from ui-glass-surfaces.json. Decorative controls only.\n'+''.join(
            f'class ACME_Glass_{e["frame"]}: ACME_TransfusionRoundedFrame {{ idc = {e["frame"]}; }};\n' for e in dialog['targets'])
        path=ROOT/'addons/acm_extended/ui/glass'/(dialog['dialog']+'.hpp')
        if args.check:
            if path.read_text()!=expected:raise SystemExit(f'Stale glass pool: {path}')
        else:path.write_text(expected)
    print(f'Glass pools: {len(manifest["dialogs"])} verified' if args.check else 'Glass pools generated')
if __name__=='__main__':main()
