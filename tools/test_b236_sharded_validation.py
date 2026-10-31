"""Sharding must retain coverage and cannot turn baseline failures into approval."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import pytest
import run_sharded_regressions as m

@pytest.mark.parametrize('n',[1,4,8,12])
def test_every_module_is_allocated_exactly_once_and_stably(n):
    modules=[f'tools/test_{i}.py' for i in range(301)]
    splits=[m.allocation(modules,n,s) for s in range(n)]
    assert sorted(p for part in splits for p in part)==sorted(modules)
    assert all(m.allocation(list(reversed(modules)),n,s)==list(reversed(splits[s])) for s in range(n))

@pytest.mark.parametrize('count,shard',[(0,0),(-1,0),(4,-1),(4,4)])
def test_invalid_allocations_fail(count,shard):
    with pytest.raises(ValueError):m.allocation([],count,shard)


def test_discovery_has_no_upper_build_cutoff_and_retains_manifest(tmp_path):
    for name in ['tools/test_legacy.py','addons/acm_extended/tools/test_b237_new.py','addons/acm_extended/tools/test_b9999_future.py']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('')
    (tmp_path/'tools/current-regression-selection.txt').write_text('tools/test_legacy.py\n')
    assert len(m.current_selection(tmp_path))==3


def fixture_reports(tmp_path,monkeypatch,failed=False):
    repo=tmp_path/'repo';out=tmp_path/'results';(repo/'tools').mkdir(parents=True);out.mkdir()
    (repo/'tools/current-regression-selection.txt').write_text('tools/test_current.py\n')
    (repo/'tools/test_current.py').write_text('')
    (repo/'tools/test_old.py').write_text('')
    monkeypatch.setattr(m,'GROUPS',{'root':('tools',1)})
    files=m.discover(repo,'root');folder=out/'root-0';folder.mkdir()
    for label in ('before','after'):
        root=ET.Element('testsuite',name=label)
        ET.SubElement(root,'testcase',classname='tools.test_current',name='test_ok')
        case=ET.SubElement(root,'testcase',classname='tools.test_old',name='test_legacy')
        if failed:ET.SubElement(case,'failure',message='inherited failure').text='unchanged'
        ET.ElementTree(root).write(folder/(label+'.xml'))
    report=dict(group='root',shard=0,count=1,baseline_modules=files,current_modules=files,
        baseline_inventory=files,current_inventory=files,baseline_exit=int(failed),current_exit=int(failed),
        parity_passed=True,comparison=dict(problems=[]))
    m.save(folder/'comparison.json',report)
    return repo,out,folder,report


def test_unchanged_failure_allows_parity_but_never_strict_release(tmp_path,monkeypatch):
    repo,out,folder,_=fixture_reports(tmp_path,monkeypatch,True)
    r=m.aggregate(repo,out)
    assert r['complete'] and r['parity_passed'] and not r['strict_full_suite_passed']
    assert not r['public_release_approved'] and not r['native_accepted']
    assert len(json.loads((out/'remaining-failures.json').read_text())['records'])==1
    assert m.main(['aggregate','--repo',str(repo),'--out',str(out),'--require-green'])==1


def test_clean_full_suite_still_does_not_claim_native_acceptance(tmp_path,monkeypatch):
    repo,out,_,_=fixture_reports(tmp_path,monkeypatch)
    r=m.aggregate(repo,out)
    assert r['strict_full_suite_passed'] and not r['native_accepted']

@pytest.mark.parametrize('fault',['missing_xml','duplicate_shard','missing_shard','inventory_drift','negative_fatal','missing_current','nonpassing_current'])
def test_missing_or_untrusted_coverage_never_passes(tmp_path,monkeypatch,fault):
    repo,out,folder,report=fixture_reports(tmp_path,monkeypatch)
    if fault=='missing_xml':(folder/'after.xml').unlink()
    elif fault=='duplicate_shard':m.save(out/'duplicate/comparison.json',report)
    elif fault=='missing_shard':(folder/'comparison.json').unlink()
    elif fault=='inventory_drift':(repo/'tools/test_new.py').write_text('')
    elif fault=='negative_fatal':
        report.update(current_exit=-9,parity_passed=False,comparison={'problems':['fatal pytest exit code -9']})
        m.save(folder/'comparison.json',report)
    elif fault=='missing_current':(repo/'tools/current-regression-selection.txt').write_text('tools/test_missing.py\n')
    elif fault=='nonpassing_current':
        tree=ET.parse(folder/'after.xml');ET.SubElement(tree.getroot().find('testcase'),'skipped');tree.write(folder/'after.xml')
    r=m.aggregate(repo,out)
    assert not r['parity_passed'] and not r['strict_full_suite_passed'] and not r['public_release_approved']


def test_timeout_cannot_be_misread_as_clean_empty_report(tmp_path,monkeypatch):
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(args[0],1)
    monkeypatch.setattr(m.subprocess,'run',timeout)
    assert m.suite(tmp_path,['tools/test_one.py'],tmp_path,'after',1)==124
    assert not (tmp_path/'after.xml').exists()


def test_workflow_has_complete_matrix_and_independent_strict_gate():
    text=(Path(__file__).resolve().parents[1]/'.github/workflows/b204-network-audit.yml').read_text()
    assert text.count('          - group: addon')==8
    assert text.count('          - group: root')==4
    assert '--require-green' in text and 'fail-fast: false' in text
    assert '90e47ed7a2fc457099255f477f2b476fdae2ce9b' in text
    assert 'if-no-files-found: error' in text
    assert 'test_b216*py' not in text
