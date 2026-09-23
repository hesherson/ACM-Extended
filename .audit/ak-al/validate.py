"""Complete-checkout bounded AK-AL comparison; never update main."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, hashlib, json, os, shutil, subprocess, sys, xml.etree.ElementTree as ET

BASE='3ac65fedf7106a53be1f3703933d39e724c9de9a'
BRANCH='audit/bounded-backlog-ak-al-validated-20260923'
HERE=Path(__file__).parent
OUT=Path('/tmp/acme-ak-al-results'); OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-ak-al-before'); AFTER=Path('/tmp/acme-ak-al-after')
T='addons/acm_extended/tools/'
RUNTIME='addons/acm_extended/functions/fn_skFlushSite.sqf'
AK=T+'test_bounded_flush_patient_context.py'
AL=T+'test_bounded_flush_preview_contracts.py'
DOC_AK='docs/audits/2026-09-23-bounded-backlog-AK.md'
DOC_AL='docs/audits/2026-09-23-bounded-backlog-AL.md'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
REVIEWED={
 T+'test_b59_shared_syringe_body_carousel.py':('H233','test_flush_body_map_path_is_not_broken_by_syringe_preview','preview_contract'),
 T+'test_b63_tag_carousel_interaction.py':('H271','test_pending_tag_live_preview_remains_available_to_saline_flush_flow','tag_save_contract'),
}
SELECTED=[p+'::'+v[1] for p,v in REVIEWED.items()]
FOCUSED=[AK,AL,T+'test_bounded_site_click_handoff.py',T+'test_historical_medication_preparation.py',T+'test_historical_syringe_identity.py',T+'test_bounded_normal_push_lifetime.py',T+'test_bounded_selector_lifetime.py']+SELECTED


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=90)
    assert r.returncode==0,(args,r.stdout[-2000:],r.stderr[-2000:])
    return r.stdout.strip()


def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as f:
        r=subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(name,'exit',r.returncode,flush=True)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    rows={}
    for c in ET.parse(xml).iter('testcase'):
        key=(c.get('classname',''),c.get('name',''))
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        rows.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in rows.values(): counts.update(v)
    print(name,dict(counts),flush=True)
    return rc,rows,dict(counts)


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def revised_body(path,name,helper):
    f=AFTER/path; text=f.read_text(); tree=ast.parse(text)
    nodes=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(nodes)==1; n=nodes[0]
    lines=text.splitlines(keepends=True)
    lines[n.body[0].lineno-1:n.end_lineno]=[f'    from test_bounded_flush_preview_contracts import {helper}\n',f'    {helper}()\n']
    f.write_text(''.join(lines))
    def norm(s):
        a=ast.parse(s)
        for node in ast.walk(a):
            if isinstance(node,ast.FunctionDef) and node.name==name: node.body=[ast.Pass()]
        return ast.dump(a,include_attributes=False)
    assert norm(text)==norm(f.read_text()),'Unreviewed historical body edit'


for p,expected in [('patient.py','80fbba8523cb95d8610bc0c36be728fab2e94c05010894a1f2cf62756b778e4d'),('preview.py','fc9871d7267301e88500a054029dcf5d3b82462ae78bd45db1790c139c501177')]:
    raw=(HERE/p).read_bytes(); assert hashlib.sha256(raw).hexdigest()==expected,(p,'transport mismatch')
    compile(raw,p,'exec')
git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert tests('historical-before',BEFORE,SELECTED)[2]=={'failed':2}
for root in (BEFORE,AFTER):
    shutil.copyfile(HERE/'patient.py',root/AK);shutil.copyfile(HERE/'preview.py',root/AL)
ak_old=tests('AK-original-runtime',BEFORE,[AK]); al_old=tests('AL-original-runtime',BEFORE,[AL])
assert ak_old[2]=={'passed':13,'failed':10} and ak_old[0]==1
assert al_old[2]=={'passed':20} and al_old[0]==0
rawlog=(OUT/'AK-original-runtime.log').read_text(); assert '[ERR]' not in rawlog and '[FAT]' not in rawlog
for p in (AK,AL):(BEFORE/p).unlink()
old='private _display = findDisplay 84000;\nprivate _patient = uiNamespace getVariable ["ACME_SK_Patient", objNull];'
new='private _display = findDisplay 84000;\nif (isNull _display) exitWith {};\n// Match the patient used by the Body Map artwork and exact site-click validation.\n// Shared preparation state may have been cleared or changed since this display opened.\nprivate _patient = _display getVariable ["ACME_SK_ReturnPatient", objNull];'
f=AFTER/RUNTIME; txt=f.read_text();assert txt.count(old)==1;f.write_text(txt.replace(old,new))
for p,(_,name,helper) in REVIEWED.items():revised_body(p,name,helper)
focused=tests('focused',AFTER,FOCUSED); assert focused[0]==0 and focused[2]=={'passed':237}
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2]=={'passed':4662,'failed':97,'skipped':4},before[2]
assert after[2]=={'passed':4707,'failed':95,'skipped':4},after[2]
assert set(before[1]).issubset(after[1]),'Missing prior identity'
fixed=[]
for key,outcome in before[1].items():
    if after[1][key]==outcome:continue
    assert outcome==Counter({'failed':1}) and after[1][key]==Counter({'passed':1}),(key,outcome,after[1][key])
    fixed.append(key)
assert len(fixed)==2 and {k[1] for k in fixed}=={v[1] for v in REVIEWED.values()}
added=set(after[1])-set(before[1]);assert len(added)==43
assert all(after[1][k]==Counter({'passed':1}) for k in added)
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
assert root_after[2]=={'passed':137,'error':46}
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],150)==0
assert run('diff-check',AFTER,['git','diff','--check'],30)==0
changed={p for p,h in original.items() if hashlib.sha256((AFTER/p).read_bytes()).hexdigest()!=h}
assert changed==set(REVIEWED)|{RUNTIME},changed
report={'base':BASE,'AK_original_runtime':ak_old[2],'AL_original_runtime':al_old[2],
        'focused':focused[2],'addon_before':before[2],'addon_after':after[2],
        'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':['H233','H271'],'remaining_original_entries':67,
        'new_passing_cases':43,'missing_previous':[],'newly_failing':[],
        'runtime_files_changed':[RUNTIME],'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_AK).write_text(f'''# Bounded AK: Body Map flush uses its displayed patient

Parent: `{BASE}` (AI-AJ).

Body Map artwork and skSiteClick validate the display-local ReturnPatient (with the existing self-view fallback). skFlushSite instead read mutable shared ACME_SK_Patient. A cleared global could flush the medic rather than the displayed casualty; a different shared patient with access could receive the request instead. A missing display did not prevent dispatch.

Only skFlushSite changes runtime. Require an open draw display and use its same patient snapshot/self fallback as the artwork and exact site-click validation. No shared patient overwrite, new state, timer, handler, network event, access/distance rule, dose calculation or inventory algorithm is introduced. The unchanged salineFlush worker retains exact-site, stock, locality and same-vehicle distance checks. No patient-life restriction is added.

Twenty-three new cases execute actual skSiteClick, skFlushSite and salineFlush. On unchanged source: ten fail and thirteen pass. Candidate: all pass. Cases cover IV/IO, cleared/different/matching shared patient, live/dead casualty flags, self view, missing display, exact-access rejection, stock/locality/distance rejection, same-vehicle exception, remaining selection, request/log patient, and no mutation of stored syringes or a staged medication target.

These tests record inventory removal, medicationRequest and activity boundaries. They do not deliver parked line medications, use live inventory or test actual controls/networking. The actual patient death engine state is not simulated. Old-control events from a replaced dialog, provider changes within a live display, general site-click busy gating and same-context lifecycle round trips remain outside this narrow correction. No original H entry closes in AK. No live Arma or stable-release approval.
''')
git(AFTER,'add',RUNTIME,AK,DOC_AK)
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AK: keep Body Map flush on the displayed patient')
sha_ak=git(AFTER,'rev-parse','HEAD')
ledger=(AFTER/LEDGER).read_text(); lines=ledger.splitlines(keepends=True)
historical=[l for l in lines if l.startswith('H')];assert len(historical)==69
resolved={v[0] for v in REVIEWED.values()}
assert {l.split()[0] for l in historical if l.split()[0] in resolved}==resolved
lines=[l for l in lines if not (l.startswith('H') and l.split()[0] in resolved)]
lines[0]='Unresolved original source-contract outcomes after bounded AL: 67\n'
lines[1]='Base: '+BASE+'\n'
(AFTER/LEDGER).write_text(''.join(lines))
assert [l for l in (AFTER/LEDGER).read_text().splitlines(keepends=True) if l.startswith('H')]==[l for l in historical if l.split()[0] not in resolved]
report['AK']=sha_ak
report['changed_existing']=sorted(set(REVIEWED)|{RUNTIME,LEDGER})
report['unchanged_existing_files']=len(original)-len(report['changed_existing'])
(AFTER/DOC_AL).write_text('''# Bounded AL: shared flush preview and tag attachment at save

Builds on AK. H233 and H271 retain their original pytest identities. The old body-preview files are compatibility shims to the shared carousel; they do not duplicate the old caption/artwork. Pending preview follows the preparation page even with a stale return context. The native Waste Draw stages measured components; skFlushSave commits the pending tag and applies it to the funded saved dilution, rather than tagging on every Draw.

The reconciled bodies follow executable delegates, the dedicated flush barrel/tooltip, tag-free unmedicated flush preview, flush-enabled vascular targets without a prepared syringe, pending editor visibility and save-time tag ordering. Twenty new checks pass on unchanged runtime: six full save/tag cases for None/white/colored tags and long/short text, four actual readiness/page-prefix checks, four shim dispatch checks and six mutation controls with comment decoys. Existing source-funding, stable-identity, normal-push and selector execution tests remain included.

No rendering, native draw, source accounting, medication or configuration changes in AL. The preview branch is checked by tokens, not pixel rendering; save and geometry use declared engine substitutes. Later save/reopen callbacks, duplicate live save events, font fitting and actual inventory/network behavior are not certified. Only these two historical test bodies and H entries change. No skip or xfail added; index 69 to 67. No live Arma or stable-release approval.

## Complete-checkout validation

```json
'''+json.dumps(report,indent=2)+'''
```

Full addon and root suites still fail overall. Every prior raw JUnit identity is retained without new failures. Protected snapshots, all other runtime/configuration and assets are unchanged. HEMTT check is not a release-package or live-engine acceptance test.
''')
git(AFTER,'add',*REVIEWED,AL,LEDGER,DOC_AL)
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AL: reconcile shared flush preview and tag-save contracts')
assert not git(AFTER,'status','--porcelain')
final=manifest(AFTER)
assert {p for p,h in original.items() if final.get(p)!=h}==set(report['changed_existing'])
assert set(final)-set(original)=={AK,AL,DOC_AK,DOC_AL}
assert run('committed-diff-check',AFTER,['git','diff','--check',BASE,'HEAD'],30)==0
report.update({'AL':git(AFTER,'rev-parse','HEAD'),'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2));(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('AK-AL: displayed-patient flush correction and two historical contract reconciliations. Separate patches, full before/after logs/JUnit and SHA256 manifests. No stable-release approval.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
