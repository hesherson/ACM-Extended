"""Validate exact reviewed pose cleanup source; publish an audit candidate only.

Every historical failure remains visible. Runtime allowlist, exact tree, previous
outcomes and old/new execution controls are required; main is never updated here.
"""
import ast,hashlib,json,lzma,os,re,shutil,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path.cwd();INFRA=ROOT/'.audit/historical-batch12'
BASE='c7fc94d1501ab4acee0dde86fc60caa48cba5f33'
TREE='385ad6b8ec1734d752ce66ee7e850cd4f31b6050'
CANDIDATE=Path('/tmp/acme-backlog12-candidate');BASELINE=Path('/tmp/acme-backlog12-baseline')
RESULTS=Path('/tmp/acme-backlog12-results');RESULTS.mkdir(exist_ok=True)
PREFIX='addons/acm_extended/tools/'
RUNTIME='addons/acm_extended/functions/fn_treatmentPoseStop.sqf'
NEW=PREFIX+'test_historical_pose_lifecycle.py'
PROTECTION='tools/test_self_audit_20260922.py'
DOC='docs/audits/2026-09-22-historical-backlog-batch12.md'
INDEX='docs/audits/historical-backlog-remaining-20260922.txt'

def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def run(label,command,root,env=None):
    with (RESULTS/(label+'.log')).open('w') as out:
        cp=subprocess.run(command,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=480)
    (RESULTS/(label+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(label,'exit',cp.returncode,flush=True);print((RESULTS/(label+'.log')).read_text()[-1800:],flush=True)
    return cp.returncode
subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for p in (CANDIDATE,BASELINE):subprocess.run(['git','worktree','add','--detach',str(p),BASE],check=True)
compressed=b''.join(p.read_bytes() for p in sorted(INFRA.glob('payload*.bin')))
assert hashlib.sha256(compressed).hexdigest()=='e146a50705195dc0032258694e9e15af8886626d4da9690438e75f5bd68f4e0a'
payload=json.loads(lzma.decompress(compressed));patch=payload['patch'].encode()
assert hashlib.sha256(patch).hexdigest()=='a8bb5bed58a763414a4d06748a937e3b9c3993939e48c9b5ab5dab259506b46d'
patchfile=RESULTS/'transport.patch';patchfile.write_bytes(patch)
for args in (['apply','--check',str(patchfile)],['apply',str(patchfile)]):
    subprocess.run(['git',*args],cwd=CANDIDATE,check=True)
# The unrelated protected hashes are deliberately not part of the transfer patch.
# Permit exactly the one digest update for the reproduced runtime guard.
h=payload['protected_hash'];assert h['path']==RUNTIME
p=CANDIDATE/PROTECTION;a=p.read_text();assert a.count(h['old'])==1
p.write_text(a.replace(h['old'],h['new'],1))
assert hashlib.sha256((CANDIDATE/RUNTIME).read_bytes()).hexdigest()==h['new']
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
full=subprocess.check_output(['git','diff','--cached','--binary','--full-index'],cwd=CANDIDATE)
assert hashlib.sha256(full).hexdigest()=='455b629d8e48af106bd264fdf7f949b30daae0f4299c30d72230481589eea876'
(RESULTS/'reviewed.patch').write_bytes(full)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
expected={RUNTIME,NEW,PROTECTION,DOC,INDEX}|{PREFIX+n for n in payload['test_scope']}
assert len(changes)==9 and {s.split('\t')[1] for s in changes}==expected
assert all(s.split('\t')[0] in ('A','M') for s in changes)
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
old='            if (!isNull objectParent _unit) exitWith {};\n            if (stance _unit == "STAND") then {'
new='            if (!isNull objectParent _unit) exitWith {};\n            // A newer controller may own stance without incrementing the treatment-pose epoch.\n            if ([_unit] call ACME_fnc_providerStanceOwned) exitWith {};\n            if (stance _unit == "STAND") then {'
a=(BASELINE/RUNTIME).read_text();b=(CANDIDATE/RUNTIME).read_text()
assert a.count(old)==1 and b==a.replace(old,new,1)

def tests(text):
    out={}
    def visit(nodes,prefix=''):
        for node in nodes:
            if isinstance(node,ast.ClassDef):visit(node.body,prefix+node.name+'::')
            elif isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
                assert prefix+node.name not in out
                out[prefix+node.name]=ast.dump(node,include_attributes=False)
    visit(ast.parse(text).body);return out
scope={}
for path,names in payload['test_scope'].items():
    a=tests((BASELINE/PREFIX/path).read_text());b=tests((CANDIDATE/PREFIX/path).read_text());assert a.keys()==b.keys()
    changed={k for k in a if a[k]!=b[k]}
    assert {k.split('::')[-1] for k in changed}==set(names)
    scope[path]=sorted(changed)
assert sum(map(len,scope.values()))==10
# All other golden digests and tests in this file must match as complete text.
a=(BASELINE/PROTECTION).read_text();b=(CANDIDATE/PROTECTION).read_text()
assert b==a.replace(h['old'],h['new'],1)
unchanged=len(set(git('ls-tree','-r','--name-only',BASE,cwd=CANDIDATE).splitlines())-expected)
assert unchanged==4034,unchanged
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime':[RUNTIME],'unchanged_existing_paths':unchanged,'deleted_files':[],'test_scope':scope,'protected_hash_update':h},indent=2))
print('Exact tree and two-line runtime change verified; other protected hashes and tests unchanged.',flush=True)
focused=payload['focused'];assert len(focused)==158
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run('focused',[sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE)==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite.attrib['tests']=='1943' and all(suite.attrib[k]=='0' for k in ('errors','failures','skipped')),suite.attrib
assert run('hemtt',[os.environ['HEMTT'],'check'],CANDIDATE)==0
for label,p in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    assert run(label,[sys.executable,'-m','pytest',PREFIX.rstrip('/'),'-q','--tb=short','--continue-on-collection-errors','-p','auditrecorder'],p,env)==1
from compare import compare
summary=compare(RESULTS);(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
assert summary['fixed_count']==10 and set(summary['fixed'])==set(payload['selected'])
assert not summary['regressions'] and not summary['missing'] and not summary['new_failures'] and not any(summary['errors'].values())
assert summary['skips']=={'before':4,'after':4}
shutil.copyfile(CANDIDATE/NEW,BASELINE/NEW)
try:
    assert run('new-red',[sys.executable,'-m','pytest',NEW,'-q','--tb=short','--junitxml='+str(RESULTS/'new-red.xml')],BASELINE)==1
    red=ET.parse(RESULTS/'new-red.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='101' and red.attrib['failures']=='11' and all(red.attrib[k]=='0' for k in ('errors','skipped')),red.attrib
finally:(BASELINE/NEW).unlink()
assert run('new-green',[sys.executable,'-m','pytest',NEW,'-q','--tb=short','--junitxml='+str(RESULTS/'new-green.xml')],CANDIDATE)==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
# Publish only tested source, without audit workflow/payload. Never main or a force push.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Guard delayed pose cleanup and verify historical freeze contracts (batch 12)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch12-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
