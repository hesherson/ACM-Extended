"""Reconstruct the exact reviewed candidate and retain all historical failures.

Never advance main. Only a validated isolated branch is published. No unselected
historical test is rewritten, removed, skipped or marked expected-failure.
"""
import ast,hashlib,json,lzma,os,re,shutil,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path.cwd();INFRA=ROOT/'.audit/historical-batch11'
BASE='215d5187e6c8caaf57681edc0707e93e5f6abd98'
TREE='2975b076766cea0e0ef920ed707d2f4df6dac673'
CANDIDATE=Path('/tmp/acme-backlog11-candidate');BASELINE=Path('/tmp/acme-backlog11-baseline')
RESULTS=Path('/tmp/acme-backlog11-results');RESULTS.mkdir(exist_ok=True)
PREFIX='addons/acm_extended/tools/'
RUNTIME={'addons/acm_extended/functions/fn_medicationCBRNTick.sqf','addons/circulation/functions/fnc_setIVLocal.sqf'}
NEW_TESTS=[PREFIX+'test_historical_medication_effects.py',PREFIX+'test_historical_medication_retirement.py']
DOC='docs/audits/2026-09-22-historical-backlog-batch11.md'

def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def run(label,command,root,env=None):
    with (RESULTS/(label+'.log')).open('w') as out:
        cp=subprocess.run(command,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=480)
    (RESULTS/(label+'.command.json')).write_text(json.dumps({'command':command,'exit':cp.returncode},indent=2))
    print(label,'exit',cp.returncode,flush=True);print((RESULTS/(label+'.log')).read_text()[-2500:],flush=True)
    return cp.returncode
subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for p in (CANDIDATE,BASELINE):subprocess.run(['git','worktree','add','--detach',str(p),BASE],check=True)
compressed=b''.join(p.read_bytes() for p in sorted(INFRA.glob('payload*.bin')))
assert hashlib.sha256(compressed).hexdigest()=='c574348a8c196a7d09efe704da426df690fdb193268df13f72450b68af7f9960'
payload=json.loads(lzma.decompress(compressed));patch=payload['patch'].encode()
assert hashlib.sha256(patch).hexdigest()=='105bbcb358a9ab04fae4bfa06f33d23d89c092a7fc3ca9efd0bc945e0aceb1ae'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
for args in (['apply','--check',str(patchfile)],['apply',str(patchfile)],['add','-A']):
    subprocess.run(['git',*args],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
expected=RUNTIME|set(NEW_TESTS)|{PREFIX+'test_na8_5_batch13.py',DOC}
assert len(changes)==6
assert {s.split('\t')[1] for s in changes}==expected
assert all(s.split('\t')[0] in ('A','M') for s in changes)
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
# Exactly two single-line runtime replacements, nothing else.
for path,old,new in [
 ('addons/acm_extended/functions/fn_medicationCBRNTick.sqf','[QGVAR(AirwaySpasm), false, true]','[QEGVAR(CBRN,AirwaySpasm), false, true]'),
 ('addons/circulation/functions/fnc_setIVLocal.sqf','_bagIV != _iv','_bagIV isNotEqualTo _iv')]:
    a=(BASELINE/path).read_text();b=(CANDIDATE/path).read_text()
    assert a.count(old)==1 and b==a.replace(old,new,1),path
# Preserve entire unselected test functions, not merely their names.
def tests(text):
    out={}
    for cls in ast.parse(text).body:
        if not isinstance(cls,ast.ClassDef):continue
        for node in cls.body:
            if isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
                out[cls.name+'::'+node.name]=ast.dump(node,include_attributes=False)
    return out
path=PREFIX+'test_na8_5_batch13.py';a=tests((BASELINE/path).read_text());b=tests((CANDIDATE/path).read_text())
assert a.keys()==b.keys()
changed={k for k in a if a[k]!=b[k]};allowed={n.split('test_na8_5_batch13.py::')[1] for n in payload['selected']}
assert changed==allowed and len(changed)==9
unchanged=len(set(git('ls-tree','-r','--name-only',BASE,cwd=CANDIDATE).splitlines())-expected)
assert unchanged==4035,unchanged
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime':sorted(RUNTIME),'unchanged_existing_paths':unchanged,'deleted_files':[],'changed_historical_bodies':sorted(changed)},indent=2))
print('Exact tree, two-line runtime scope, and unrelated tests verified.',flush=True)
focused=payload['focused'];assert len(focused)==147
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run('focused',[sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE)==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite.attrib['tests']=='1832' and all(suite.attrib[k]=='0' for k in ('errors','failures','skipped')),suite.attrib
assert run('hemtt',[os.environ['HEMTT'],'check'],CANDIDATE)==0
for label,p in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    assert run(label,[sys.executable,'-m','pytest',PREFIX.rstrip('/'),'-q','--tb=short','--continue-on-collection-errors','-p','auditrecorder'],p,env)==1
from compare import compare
summary=compare(RESULTS);(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
assert summary['fixed_count']==9 and set(summary['fixed'])==set(payload['selected'])
assert not summary['regressions'] and not summary['missing'] and not summary['new_failures'] and not any(summary['errors'].values())
assert summary['skips']=={'before':4,'after':4}
for p in NEW_TESTS:shutil.copyfile(CANDIDATE/p,BASELINE/p)
try:
    assert run('new-red',[sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'new-red.xml')],BASELINE)==1
    red=ET.parse(RESULTS/'new-red.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='135' and red.attrib['failures']=='18' and all(red.attrib[k]=='0' for k in ('errors','skipped')),red.attrib
finally:
    for p in NEW_TESTS:(BASELINE/p).unlink()
assert run('new-green',[sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'new-green.xml')],CANDIDATE)==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
# Publish tested source only, without temporary workflows or payloads.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix native CBRN spasm and catheter bag boundaries; verify medication backlog (batch 11)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch11-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Isolated verified source:',commit,flush=True)
