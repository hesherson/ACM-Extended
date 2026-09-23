"""Build two small review commits from a pinned baseline; never write the release branch."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = 'a488723656d8a370184df56209e55a17bc3901ef'
REPO = Path('/tmp/acme-bounded-candidate')
OUT = Path('/tmp/acme-bounded-results')
OUT.mkdir(exist_ok=True)
SOURCE = Path('addons/acm_extended/functions/fn_stethoscopeClose.sqf')
EXISTING = Path('addons/acm_extended/tools/test_stethoscope_exit_recovery_20260921.py')
NEW = Path('addons/acm_extended/tools/test_bounded_stethoscope_exit_generation.py')
ROOT_TEST = Path('tools/test_fork_phase150_flip_cancel.py')
BRANCH = 'audit/bounded-backlog-validated-20260923'
TEST = Path(__file__).with_name('stethoscope_execution.txt').read_text()
compile(TEST, str(NEW), 'exec')


def command(args, cwd=None, timeout=120, check=True):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'{args}: {result.returncode}\n{result.stdout[-12000:]}')
    return result


def record(name, args, timeout=120):
    result = command(args, REPO, timeout, check=False)
    (OUT / f'{name}.log').write_text(result.stdout)
    print(f'=== {name}: exit {result.returncode} ===\n{result.stdout[-3500:]}', flush=True)
    return result.returncode


def outcomes(path):
    result = {}
    for case in ET.parse(path).iter('testcase'):
        key = (case.get('classname', ''), case.get('name', ''))
        status = 'error' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        assert key not in result, f'duplicate identity {key}'
        result[key] = status
    return result


def pytest(name, paths):
    xml = OUT / f'{name}.xml'
    rc = record(name, [sys.executable, '-m', 'pytest', *map(str, paths), '-q',
                       '--continue-on-collection-errors', '--tb=short', f'--junitxml={xml}'], 150)
    data = outcomes(xml)
    counts = {kind: list(data.values()).count(kind) for kind in ['passed','failed','error','skipped']}
    print(name, json.dumps(counts), flush=True)
    return rc, data, counts


def replace_once(path, old, new):
    text = (REPO / path).read_text()
    assert text.count(old) == 1, f'unreviewed source at {path}'
    (REPO / path).write_text(text.replace(old, new))


def tracked_manifest():
    files = command(['git','ls-files','-z'], REPO).stdout.split('\0')
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in files if p}


command(['git','fetch','--depth=1','origin',BASE])
command(['git','worktree','add','--detach',str(REPO),BASE])
assert command(['git','rev-parse','HEAD'],REPO).stdout.strip() == BASE
original = tracked_manifest()
(OUT / 'baseline-manifest.json').write_text(json.dumps(original, indent=2))
focused = [EXISTING, 'addons/acm_extended/tools/test_historical_chest_workspace.py',
           'addons/acm_extended/tools/test_menu_death_lifecycle.py']
before_rc, before, before_counts = pytest('focused-before', focused)
expected_failure = next(k for k in before if k[1] == 'test_unload_clears_matching_continuous_action_and_pose')
assert before_rc == 1 and {k for k,v in before.items() if v != 'passed'} == {expected_failure}
root_before_rc, root_before, root_before_counts = pytest('root-before', ['tools'])

# Execute new cases on unchanged runtime before modifying production source.
(REPO / NEW).write_text(TEST)
old_rc, old_control, old_counts = pytest('unchanged-source-control', [NEW])
assert old_rc == 1 and old_counts == {'passed':15,'failed':10,'error':0,'skipped':0}, old_counts
old_log = (OUT / 'unchanged-source-control.log').read_text()
assert 'wrong-generation provider exit' in old_log
assert '[ERR]' not in old_log and '[FAT]' not in old_log

# Batch A: generation-scope only the final provider presentation handoff.
replace_once(SOURCE,
    'if (!isNull _medic && {local _medic} && {alive _medic}\n',
    '// A superseded display must not start its exit over a newer continuous action.\n'
    '// Use the scope generation here: an active Flip legitimately owns a newer roll pose epoch.\n'
    'if (_continuousEpoch >= 0\n'
    '    && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",-2]) == _continuousEpoch}\n'
    '    && {!isNull _medic} && {local _medic} && {alive _medic}\n')
replace_once(EXISTING,
    '[_medic,"stethoscope",_poseEpoch] call ACME_fnc_treatmentPoseStop;',
    '[_medic,"stethoscope",_poseEpoch,true] call ACME_fnc_treatmentPoseStop;')
after_rc, after, after_counts = pytest('focused-after', focused + [NEW])
assert after_rc == 0 and set(after.values()) == {'passed'}, after_counts
assert set(before).issubset(after) and all(after[k] == 'passed' for k in before)
assert record('hemtt', [os.environ['HEMTT'], 'check'], 150) == 0

# Batch B: retain the root assertions but match the existing explicit supine signature.
replace_once(ROOT_TEST,
    "assert '[_patient] call ACME_fnc_patientRollCancel;' in steth_close",
    "assert '[_patient,\"front\"] call ACME_fnc_patientRollCancel;' in steth_close")
assert record('phase150-direct', [sys.executable, str(ROOT_TEST)], 30) == 0
root_after_rc, root_after, root_after_counts = pytest('root-after', ['tools'])
removed = set(root_before) - set(root_after)
assert len(removed) == 1 and all('test_fork_phase150_flip_cancel' in ' '.join(k) and root_before[k] == 'error' for k in removed), removed
assert set(root_after).issubset(root_before)
assert all(root_after[k] == root_before[k] for k in root_after), 'root outcome regression'
assert root_after_rc == root_before_rc == 1, 'root suite unexpectedly changed exit status'

# Exact preservation includes the untouched original backlog and snapshot manifests.
allowed = {str(SOURCE),str(EXISTING),str(ROOT_TEST)}
current = tracked_manifest()
changed = {p for p in original if original[p] != current.get(p)}
assert changed == allowed, changed
assert set(current) == set(original), 'deleted or unexpected tracked files'
(OUT / 'preservation.json').write_text(json.dumps({'changed':sorted(changed),'unchanged_existing':len(original)-len(changed),'baseline_files':len(original),'deleted':[]},indent=2))
report = {'baseline':BASE,'focused_before':before_counts,'focused_after':after_counts,
          'old_source_control':old_counts,'root_before':root_before_counts,'root_after':root_after_counts,
          'hemtt_exit':0,'full_addon_suite_rerun':False,
          'original_unresolved_source_contract_index':146,'release_approved':False}

DOC_A = Path('docs/audits/2026-09-23-bounded-backlog-A.md')
DOC_B = Path('docs/audits/2026-09-23-bounded-backlog-B.md')
(REPO / DOC_A).write_text('''# Bounded continuation A: stethoscope provider exit generation

Baseline: `''' + BASE + '''` (published batch 14). This continuation is separately named to avoid claiming integration of an unavailable, reportedly unpushed batches 15-17 package.

## Confirmed defect and correction

The complete stethoscope Unload function already guarded continuous-action teardown, but its final `headElevMedicSeq` lower request was outside that guard. A superseded display could therefore issue the authored provider exit over a newer continuous action. The same captured continuous-action generation now gates that final request. The pose epoch is deliberately not substituted: an active Flip legitimately advances the roll pose within the same scope session.

Only this final guard changes runtime behavior. Existing normal Putdown/inventory/crouch choreography, speed release, active Flip cancellation, supine requests, carrier restoration routing, dead-patient equipment routing, cursor code, audio code, physiology and medication code remain unchanged.

The existing failing stethoscope exit test now expects the current four-argument treatment-pose handoff (`true`) rather than demanding the obsolete three-argument generic exit. Its identity and other assertions are retained. This is contract reconciliation, not a newly discovered handoff defect.

## Executed validation

Twenty-five new cases execute the complete actual Unload SQF through the existing SQF-VM harness. Unchanged runtime produces exactly 10 intended failures and 15 passing controls. Candidate runtime passes all 25. Cases include missing/stale/current generations, independent pose epochs, normal and active-Flip exit, absent/present carrier handoffs, live/dead patients, and provider locality, vehicle, consciousness, life and existing-sequence exclusions. Existing chest-workspace and menu-lifecycle execution tests also remain in the focused selection.

Focused before: ''' + json.dumps(before_counts) + '''. Focused after: ''' + json.dumps(after_counts) + '''. HEMTT check returns 0. Exact before/after identities are retained in the evidence artifact. No new skip or expected-failure marker is added. Every other existing tracked file remains unchanged apart from the separately documented Batch B root-test assertion.

## Boundaries

The fixtures record engine-boundary calls; they do not render an Arma animation or test real display scheduling, network traffic or hearing gain. Patient animation-lease release, carrier-lease identity, stale active-Flip cancellation and hearing restoration elsewhere in Unload are not certified by this narrow correction. No full historical addon suite was rerun in this bounded pass. The last published 175-failure aggregate is not replaced with an inferred total. The 146-entry original source-contract index is unchanged. This is not stable-release approval.
''')
command(['git','add',str(SOURCE),str(EXISTING),str(NEW),str(DOC_A)],REPO)
command(['git','-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Guard stethoscope provider exit by continuous generation (bounded A)'],REPO)
commit_a = command(['git','rev-parse','HEAD'],REPO).stdout.strip()
(REPO / DOC_B).write_text('''# Bounded continuation B: retain the explicit supine Flip-cancel contract

Parent: `''' + commit_a + '''`.

The root phase-150 test still required the former one-argument `patientRollCancel` call. Runtime already requests `[patient, "front"]` to preserve the required supine exit. Change that one assertion, retaining the rest of the root script byte-for-byte. Do not restore the old call or drop the assertion. The Batch A full-Unload execution tests also verify the actual anterior-up cancellation request during an active Flip and retain ordinary no-Flip controls.

The root script now executes successfully. Entire root-tools probe before: ''' + json.dumps(root_before_counts) + '''. After: ''' + json.dumps(root_after_counts) + '''. Exactly the phase-150 collection error disappears; every other comparable root identity has the same outcome. Both broad root commands still return 1. Remaining root errors are open, not waived. This does not change the separate historical addon-suite failure aggregate or its original source-contract ledger.

No runtime file changes in this batch. No Arma client, dedicated server or release package was run or approved.
''')
command(['git','add',str(ROOT_TEST),str(DOC_B)],REPO)
command(['git','-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Align root flip-cancel test with explicit supine request (bounded B)'],REPO)
commit_b = command(['git','rev-parse','HEAD'],REPO).stdout.strip()
assert not command(['git','status','--porcelain'],REPO).stdout.strip(), 'candidate not clean'
report.update({'commit_A':commit_a,'commit_B':commit_b,'tree':command(['git','rev-parse','HEAD^{tree}'],REPO).stdout.strip(),'review_branch':BRANCH})
(OUT / 'report.json').write_text(json.dumps(report,indent=2))
(OUT / 'candidate.patch').write_text(command(['git','diff',BASE,commit_b],REPO).stdout)
command(['git','format-patch','--output-directory',str(OUT),BASE+'..'+commit_b],REPO)
(OUT / 'candidate-files.json').write_text(json.dumps({p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in [str(SOURCE),str(EXISTING),str(NEW),str(ROOT_TEST),str(DOC_A),str(DOC_B)]},indent=2))
command(['git','push','origin',f'HEAD:refs/heads/{BRANCH}'],REPO)
print('VALIDATED_REVIEW_CANDIDATE',json.dumps(report,indent=2),flush=True)
