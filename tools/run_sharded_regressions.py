#!/usr/bin/env python3
"""Complete bounded regression comparison and an independent strict release gate.

All discovered modules are assigned exactly once. Timeouts, missing reports,
new failures/skips or disappeared cases fail comparison. Inherited failures are
reported explicitly and NEVER make the strict full-suite/release gate pass.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional
import xml.etree.ElementTree as ET
from compare_pytest_outcomes import read_report, compare_reports, require_all_pass

GROUPS = {'addon': ('addons/acm_extended/tools', 8), 'root': ('tools', 4)}
BASELINE = '90e47ed7a2fc457099255f477f2b476fdae2ce9b'

def discover(repo: Path, group: str) -> list[str]:
    directory, _ = GROUPS[group]
    return sorted(p.relative_to(repo).as_posix() for p in (repo/directory).rglob('test_*.py'))

def allocation(modules: list[str], count: int, shard: int) -> list[str]:
    if count <= 0 or not 0 <= shard < count:
        raise ValueError('Invalid shard/count')
    return [p for p in modules if int(hashlib.sha256(p.encode()).hexdigest(), 16) % count == shard]

def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def suite(repo: Path, modules: list[str], out: Path, label: str, timeout: int) -> int:
    if not modules:
        raise ValueError(f'Empty suite: {label}')
    cmd = [sys.executable, '-m', 'pytest', *modules, '--rootdir', str(repo), '-q', '--tb=short',
           '--continue-on-collection-errors', f'--junitxml={out / (label+".xml")}']
    with (out/(label+'.log')).open('w', encoding='utf-8') as log:
        try:
            result = subprocess.run(cmd, cwd=repo, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            log.write('\nERROR: full regression shard timed out; no absent report is accepted.\n');code=124
    (out/(label+'.exit')).write_text(str(code)+'\n')
    return code

def shard_run(repo: Path, baseline: Path, group: str, shard: int, out: Path, timeout: int = 600) -> bool:
    _, count = GROUPS[group]
    out.mkdir(parents=True, exist_ok=True)
    old_all, new_all = discover(baseline,group), discover(repo,group)
    old, new = allocation(old_all,count,shard), allocation(new_all,count,shard)
    meta = dict(group=group,shard=shard,count=count,baseline_modules=old,current_modules=new,
                baseline_inventory=old_all,current_inventory=new_all,timeout=timeout)
    save(out/'allocation.json',meta)
    old_exit=suite(baseline,old,out,'before',timeout)
    new_exit=suite(repo,new,out,'after',timeout)
    before,after=read_report(out/'before.xml',old_exit),read_report(out/'after.xml',new_exit)
    result=compare_reports(before,after)
    report=dict(**meta,baseline_exit=old_exit,current_exit=new_exit,comparison=asdict(result),
                counts=dict(baseline=before.counts(),current=after.counts()),parity_passed=result.passed)
    save(out/'comparison.json',report)
    print(f'{group}/{shard}: parity={result.passed}; {report["counts"]}; historical failures retained={len(result.known_baseline_failures)}')
    return result.passed

def current_selection(repo: Path) -> list[str]:
    # Retain the audited manifest, and automatically include future build tests.
    paths={line.strip() for line in (repo/'tools/current-regression-selection.txt').read_text().splitlines()
           if line.strip() and not line.lstrip().startswith('#')}
    for group in GROUPS:
        for p in discover(repo,group):
            match=re.match(r'test_b(\d+)',Path(p).name)
            if match and int(match[1])>=203:paths.add(p)
    return sorted(paths)

def aggregate(repo: Path, out: Path) -> dict:
    expected={(g,s) for g,(_,n) in GROUPS.items() for s in range(n)}
    reports={}
    problems=[]
    for path in out.rglob('comparison.json'):
        report=json.loads(path.read_text());key=report.get('group'),report.get('shard')
        if key not in expected or key in reports:
            problems.append(f'Unexpected/duplicate shard report: {path}');continue
        reports[key]=(path.parent,report)
    if set(reports)!=expected:problems.append(f'Missing shards: {sorted(expected-set(reports))}')
    old_root,new_root=ET.Element('testsuites'),ET.Element('testsuites')
    old_exit=new_exit=0
    for group in GROUPS:
        gathered_before=[];gathered_after=[];inventories=[]
        for key,(folder,report) in sorted(reports.items()):
            if key[0]!=group:continue
            if not report.get('parity_passed'):
                problems.extend(f'{key}: {v}' for v in report.get('comparison',{}).get('problems',['Shard comparison failed']))
            gathered_before+=report['baseline_modules'];gathered_after+=report['current_modules']
            inventories.append(report['baseline_inventory'])
            if report['current_inventory']!=discover(repo,group):problems.append(f'{key}: candidate inventory changed since run')
            for label,root in (('before',old_root),('after',new_root)):
                xml=folder/(label+'.xml')
                try:
                    parsed=ET.parse(xml).getroot()
                    root.extend(list(parsed) if parsed.tag=='testsuites' else [parsed])
                except (OSError,ET.ParseError):problems.append(f'Missing/malformed {xml}')
            old_exit=max(old_exit,report['baseline_exit']);new_exit=max(new_exit,report['current_exit'])
        if sorted(gathered_after)!=discover(repo,group):problems.append(f'{group}: candidate modules omitted or repeated')
        if inventories and (any(i!=inventories[0] for i in inventories) or sorted(gathered_before)!=inventories[0]):
            problems.append(f'{group}: baseline modules omitted or repeated')
    before_path,after_path=out/'complete-before.xml',out/'complete-after.xml'
    ET.ElementTree(old_root).write(before_path,encoding='utf-8',xml_declaration=True)
    ET.ElementTree(new_root).write(after_path,encoding='utf-8',xml_declaration=True)
    before,after=read_report(before_path,old_exit),read_report(after_path,new_exit)
    comparison=compare_reports(before,after)
    strict=require_all_pass(after)
    selection=current_selection(repo)
    selected=[]
    for path in selection:
        module=path.removesuffix('.py').replace('/','.')
        cases=[c for c in after.cases if c.identity.classname==module or c.identity.classname.startswith(module+'.')]
        if not cases:problems.append(f'No executed cases for required current module: {path}')
        for case in cases:
            selected.append(case.identity.display())
            if case.state!='passed':problems.append(f'Current-candidate gate: {case.identity.display()} = {case.state}')
    failures=[]
    for case in new_root.iter('testcase'):
        node=case.find('failure');kind='failed'
        if node is None:node=case.find('error');kind='error'
        if node is not None:
            failures.append(dict(classname=case.get('classname',''),name=case.get('name',''),state=kind,
                                 message=node.get('message',''),detail=node.text or '',disposition='OPEN_REVIEW_REQUIRED'))
    save(out/'remaining-failures.json',dict(records=failures))
    result=dict(complete=not problems,counts=dict(baseline=before.counts(),current=after.counts()),
        comparison=asdict(comparison),parity_passed=comparison.passed and not problems,
        current_gate_cases=len(set(selected)),current_gate_modules=len(selection),problems=problems,
        strict_full_suite_passed=strict.passed and not problems,
        native_accepted=False,public_release_approved=False,
        statement='Regression parity is NOT a clean full suite or public-release approval.')
    save(out/'aggregate.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('comparison',)},indent=2))
    return result

def main(argv: Optional[list[str]]=None) -> int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    shard=sub.add_parser('shard');shard.add_argument('--repo',type=Path,default=Path.cwd());shard.add_argument('--baseline',type=Path,required=True)
    shard.add_argument('--group',choices=GROUPS,required=True);shard.add_argument('--shard',type=int,required=True)
    shard.add_argument('--out',type=Path,required=True);shard.add_argument('--timeout',type=int,default=600)
    agg=sub.add_parser('aggregate');agg.add_argument('--repo',type=Path,default=Path.cwd());agg.add_argument('--out',type=Path,required=True);agg.add_argument('--require-green',action='store_true')
    a=p.parse_args(argv)
    if a.command=='shard':return 0 if shard_run(a.repo.resolve(),a.baseline.resolve(),a.group,a.shard,a.out.resolve(),a.timeout) else 1
    r=aggregate(a.repo.resolve(),a.out.resolve())
    return 0 if r['parity_passed'] and (not a.require_green or r['strict_full_suite_passed']) else 1

if __name__=='__main__':raise SystemExit(main())
