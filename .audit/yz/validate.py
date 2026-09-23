"""Publish two scoped test-only batches only after complete-checkout validation."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

BASE='40efb4b6871844dd30aea56da96096b336ba9d23'
BRANCH='audit/bounded-backlog-yz-validated-20260923'
HERE=Path(__file__).resolve().parent
BEFORE=Path('/tmp/acme-yz-before'); AFTER=Path('/tmp/acme-yz-after')
OUT=Path('/tmp/acme-yz-results'); OUT.mkdir(exist_ok=True)
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
NEW_Y=T+'test_bounded_tag_font_fallback.py'; NEW_Z=T+'test_bounded_editor_presentation.py'
DOC_Y='docs/audits/2026-09-23-bounded-backlog-Y.md'; DOC_Z='docs/audits/2026-09-23-bounded-backlog-Z.md'
ITEMS={
'Y':{'test_b58_syringe_carousel_tags.py':['test_font_binary_not_redistributed_and_handwriting_fallback_is_runtime_safe'],
     'test_b64_syringe_tag_carousel_refinement.py':['test_qephillips_is_wired_as_the_tag_font_without_redistributing_font_files'],
     'test_b66_syringe_carousel_main_tag.py':['test_runtime_font_fallback_prevents_invisible_tag_typing'],
     'test_b72_chest_tag_head_provider.py':['test_new_qedavemergens_font_replaces_old_runtime_wiring']},
'Z':{'test_b63_tag_carousel_interaction.py':['test_tag_editors_are_frameless_short_and_raised','test_stored_tag_editor_raises_native_syringe_and_places_select_tag_under_tag'],
     'test_b64_syringe_tag_carousel_refinement.py':['test_tag_edit_fields_have_no_black_rect_and_text_is_larger'],
     'test_b68_syringe_tag_push_layout.py':['test_tag_text_is_lower_larger_and_edit_mode_uses_native_draw_position_without_body']}}
IDS={'Y':['H224','H280','H299','H349'],'Z':['H267','H268','H281','H318']}
SELECTED=[T+f+'::'+n for files in ITEMS.values() for f,names in files.items() for n in names]
REVIEWED={}
for files in ITEMS.values():
    for f,names in files.items(): REVIEWED.setdefault(T+f,[]).extend(names)


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=90)
    if r.returncode: raise RuntimeError((args,r.returncode,r.stdout,r.stderr))
    return r.stdout.strip()


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def tests(name,root,paths,timeout=420):
    xml=OUT/(name+'.xml')
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run([sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)],cwd=root,text=True,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    data={}
    for c in ET.parse(xml).iter('testcase'):
        key=(c.get('classname',''),c.get('name',''))
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        data.setdefault(key,Counter())[status]+=1
    total=Counter()
    for v in data.values(): total.update(v)
    print(name,'exit',r.returncode,dict(total),flush=True)
    return r.returncode,data,dict(total)


def rewrite(batch):
    for file,names in ITEMS[batch].items():
        p=AFTER/T/file;text=p.read_text();lines=text.splitlines(keepends=True);edits=[]
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.FunctionDef) and node.name in names:
                if batch=='Y':
                    body='    from test_bounded_tag_font_fallback import font_contract, no_outline_fonts\n    from test_bounded_tag_line_layout import layout_contract\n    font_contract(); no_outline_fonts(); layout_contract()\n'
                else:
                    body='    from test_bounded_editor_presentation import frame_contract, native_editor_contract\n    frame_contract(); native_editor_contract()\n'
                edits.append((node.lineno,node.end_lineno,body))
        assert len(edits)==len(names)
        for a,b,body in sorted(edits,reverse=True):lines[a:b]=[body]
        p.write_text(''.join(lines))


def index(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}


def update_index(batch,expected):
    p=AFTER/LEDGER;lines=p.read_text().splitlines();before=index(AFTER)
    assert all(k in before for k in IDS[batch])
    lines=[l for l in lines if not (l.startswith('H') and l.split()[0] in IDS[batch])]
    lines[0]=f'Unresolved original source-contract outcomes after bounded {batch}: {expected}'
    lines[1]='Base: '+BASE
    p.write_text('\n'.join(lines)+'\n')
    assert len(index(AFTER))==expected


def check_bodies():
    for path,names in REVIEWED.items():
        def normalized(root):
            tree=ast.parse((root/path).read_text());seen=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef) and node.name in names:
                    seen.append(node.name);node.body=[ast.Pass()]
            assert sorted(seen)==sorted(names)
            return ast.dump(tree,include_attributes=False)
        assert normalized(BEFORE)==normalized(AFTER),path


def commit(batch,paths):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',f'Reconcile current tag presentation contracts without runtime changes (bounded {batch})')
    return git(AFTER,'rev-parse','HEAD')


git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(index(BEFORE))==85
old=tests('selected-before',BEFORE,SELECTED,60)
assert old[0]==1 and old[2]=={'failed':8},old[2]
(AFTER/NEW_Y).write_text((HERE/'font.py').read_text())
(AFTER/NEW_Z).write_text((HERE/'editor.py').read_text())
controls=tests('new-cases-original-runtime',AFTER,[NEW_Y,NEW_Z],90)
assert controls[0]==0 and controls[2]=={'passed':46},controls[2]
# Y is independently runnable and does not depend on the later Z file.
rewrite('Y');update_index('Y',81)
y=tests('batch-Y',AFTER,SELECTED[:4]+[NEW_Y],90)
assert y[0]==0 and y[2]=={'passed':24},y[2]
(AFTER/DOC_Y).write_text('''# Bounded Y: current tag-font fallback and display cache

Parent: `'''+BASE+'''` (W-X). Test-only changes. H224, H280, H299 and H349 retain their original test identities.

The live family is QEDaveMergens, with Caveat selected when its optional bitmap-font descriptor is absent. The result is cached per display and shared by pending and stored render paths. Static labels and editable lines receive the same selected family. Retired QEPhillips references, a Caveat-only config requirement, obsolete text dimensions and a removed B72 setup-note path are no longer demanded. The no-outline-font-distribution guard remains and covers case-insensitive TTF/OTF/WOFF families. Existing current line geometry is checked rather than restored to old values.

Twenty new checks pass on unchanged runtime. Actual font-selection and text-control loop blocks execute with file-probe/control fixtures. Coverage includes present/absent descriptors, one probe on repeated repaint, sharing within a display but not across a new display, unchanged pending/stored payloads, all three pending/stored/static text targets, and mutation controls rejecting old family, wrong path, empty fallback, lost cache or wrong target despite comment decoys.

These tests do not render glyphs, test bitmap completeness, verify engine Caveat availability, live font fitting, IME, actual files changing during an open display, or general modal lifetime. No font assets are added or redistributed. No runtime, configuration, layout, medication, input or snapshot changes. Index 85 to 81; all other H entries remain verbatim. No skip/xfail and no live Arma or stable-release approval. Broad results are recorded in bounded Z and the evidence artifact.
''')
sha_y=commit('Y',[T+f for f in ITEMS['Y']]+[NEW_Y,DOC_Y,LEDGER])
rewrite('Z');update_index('Z',77);check_bodies()
focus=tests('focused',AFTER,SELECTED+[NEW_Y,NEW_Z,T+'test_bounded_tag_line_layout.py',T+'test_bounded_selector_geometry.py',T+'test_bounded_tag_color_focus.py',T+'test_bounded_tag_focus.py',T+'test_bounded_tag_contracts.py','tools/test_self_audit_20260922.py'],120)
assert focus[0]==0 and focus[2]=={'passed':285},focus[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2]=={'passed':4361,'failed':113,'skipped':4},before[2]
assert after[2]=={'passed':4415,'failed':105,'skipped':4},after[2]
fixed=[];regressed=[]
assert not (set(before[1])-set(after[1]))
for key,value in before[1].items():
    new=after[1][key]
    if value==new:continue
    if value==Counter({'failed':1}) and new==Counter({'passed':1}):fixed.append(key)
    else:regressed.append((key,dict(value),dict(new)))
assert not regressed,regressed
assert len(fixed)==8 and {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in SELECTED},fixed
added=set(after[1])-set(before[1])
assert len(added)==46 and all(after[1][k]==Counter({'passed':1}) for k in added)
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools'],60);b=pool.submit(tests,'root-after',AFTER,['tools'],60)
    root_before=a.result();root_after=b.result()
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
with (OUT/'hemtt.log').open('w') as stream:
    r=subprocess.run([os.environ['HEMTT'],'check'],cwd=AFTER,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
assert r.returncode==0
changed=set(REVIEWED)|{LEDGER}
current=manifest(AFTER)
assert {p for p in original if current.get(p)!=original[p]}==changed
assert all(v==index(AFTER).get(k) for k,v in index(BEFORE).items() if k not in IDS['Y']+IDS['Z'])
assert set(index(BEFORE))-set(index(AFTER))==set(IDS['Y']+IDS['Z'])
report={'base':BASE,'Y':sha_y,'new_cases_original_runtime':controls[2],'focused':focus[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':IDS['Y']+IDS['Z'],'remaining_original_entries':77,
        'fixed_previous_identities':fixed,'new_passing_cases':46,'missing_previous':[],'newly_failing':[],
        'runtime_files_changed':0,'changed_existing':sorted(changed),'unchanged_existing_files':len(original)-len(changed),
        'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_Z).write_text('''# Bounded Z: frame-free native editor and visibility ownership

Builds on Y from W-X. H267, H268, H281 and H318 retain their original test identities. Test-only changes.

The current editor has ST_NO_RECT style, transparent background/border, zero border size and three 25-character lines at the existing 0.038 height and 0.031 font scale. The stored editor uses its selected syringe's own native barrel rectangle, not an old absolute vertical offset. Current Select Syringe Tag/Edit Syringe Tag captions and tag-face anchor remain. Dynamic layout hides the Body Map while editing but must not force-show its group when editing ends; the body renderer owns child-overlay visibility. The patient header retains its existing edit-mode visibility gate.

Twenty-six new checks pass on unchanged runtime. Actual rectangle selection/validation and group-visibility blocks run with explicit control fixtures. Coverage includes all four stored sizes, edit versus ordinary mode, missing or invalid-length/nonpositive native rectangles, preserving the existing fallback, unchanged syringe data, hide-only body-group requests, and frame/size/caption/visibility mutations with comment decoys. Existing line-layout, selector-geometry, tag-focus, color-focus, writer and preservation tests remain included.

The group fixture intentionally contains no child controls. This does not render child overlays, prove font fitting, test arbitrary malformed numeric types/NaN, create native controls, or certify complete input/display lifetimes. No runtime/configuration/assets/fonts/snapshot changes, no new skip/xfail, and no live Arma or stable-release approval. Index 81 to 77; all unreviewed H entries and historical test bodies remain unchanged.

## Complete-checkout validation

'''+f'Focused: {focus[2]}. New cases on unchanged runtime: {controls[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly eight retained historical identities now pass, and all 46 new cases pass. No newly failing or missing previous identity. Both addon commands still return 1 with four unchanged skips and no collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical raw identities/outcomes. HEMTT check returns 0. All {len(original)-len(changed)} other existing tracked files retain SHA256, including every runtime/configuration/asset/snapshot file. No live Arma or release-package validation.\n')
sha_z=commit('Z',[T+f for f in ITEMS['Z']]+[NEW_Z,DOC_Z,LEDGER])
assert not git(AFTER,'status','--porcelain')
final=manifest(AFTER)
assert set(final)-set(original)=={NEW_Y,NEW_Z,DOC_Y,DOC_Z}
assert set(original).issubset(final)
report.update({'Z':sha_z,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('Y-Z source checkpoint. Test-only changes; no gameplay rebuild needed for these changes alone. Includes separate Git patches and complete-checkout test/preservation evidence. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
