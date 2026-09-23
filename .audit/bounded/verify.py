"""Validate and publish each bounded review commit without touching main."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = 'a488723656d8a370184df56209e55a17bc3901ef'
REPO = Path('/tmp/acme-bounded-candidate')
OUT = Path('/tmp/acme-bounded-results')
OUT.mkdir(exist_ok=True)
SOURCE = 'addons/acm_extended/functions/fn_stethoscopeClose.sqf'
EXISTING = 'addons/acm_extended/tools/test_stethoscope_exit_recovery_20260921.py'
NEW = 'addons/acm_extended/tools/test_bounded_stethoscope_exit_generation.py'
ROOT_TEST = 'tools/test_fork_phase150_flip_cancel.py'
SNAPSHOT = 'tools/test_self_audit_20260922.py'
BRANCH = 'audit/bounded-backlog-validated-20260923'
TEST = Path(__file__).with_name('stethoscope_execution.txt').read_text()
compile(TEST, NEW, 'exec')


def command(args, cwd=None, timeout=120, check=True):
    r = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f'{args}: {r.returncode}\n{r.stdout[-12000:]}')
    return r


def record(name, args, timeout=120):
    r = command(args, REPO, timeout, False)
    (OUT / f'{name}.log').write_text(r.stdout)
    print(f'=== {name}: exit {r.returncode} ===\n{r.stdout[-3000:]}', flush=True)
    return r.returncode


def outcomes(path):
    data = {}
    for case in ET.parse(path).iter('testcase'):
        name = case.get('name', '')
        # Parameter IDs embed the digest. Normalize only the two explicitly reviewed paths.
        # Original JUnit identities remain unmodified in the retained XML files.
        for protected in (SOURCE, ROOT_TEST):
            prefix = f'test_prior_fix_restored_without_rewrite[{protected}-'
            if name.startswith(prefix) and name.endswith(']'):
                assert re.fullmatch('[a-f0-9]{64}', name[len(prefix):-1])
                name = prefix + '<reviewed-digest>]'
        key = (case.get('classname', ''), name)
        status = 'error' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        assert key not in data, key
        data[key] = status
    return data


def pytest(name, paths):
    xml = OUT / f'{name}.xml'
    rc = record(name, [sys.executable, '-m', 'pytest', *paths, '-q',
                       '--continue-on-collection-errors', '--tb=short', f'--junitxml={xml}'], 150)
    data = outcomes(xml)
    counts = {s: list(data.values()).count(s) for s in ['passed','failed','error','skipped']}
    print(name, json.dumps(counts), flush=True)
    return rc, data, counts


def replace_once(path, old, new):
    text = (REPO / path).read_text()
    assert text.count(old) == 1, f'unreviewed source at {path}'
    (REPO / path).write_text(text.replace(old, new))


def digest(path):
    return hashlib.sha256((REPO / path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def revise_snapshot(path):
    assert path in (SOURCE, ROOT_TEST) and path not in revisions
    old, new = original[path], digest(path)
    assert old != new
    replace_once(SNAPSHOT, f"'{path}': '{old}'", f"'{path}': '{new}'")
    revisions[path] = {'before':old,'after':new}


def commit(paths, message):
    command(['git','add',*paths], REPO)
    command(['git','-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com',
             'commit','-m',message], REPO)
    sha = command(['git','rev-parse','HEAD'],REPO).stdout.strip()
    assert not command(['git','status','--porcelain'],REPO).stdout.strip(), 'unclean candidate'
    return sha


def preserve_and_publish(commits, expected_changed, expected_added):
    now = {p:digest(p) for p in original}
    changed = {p for p in original if original[p] != now[p]}
    assert changed == set(expected_changed), changed
    tracked = set(filter(None, command(['git','ls-files','-z'],REPO).stdout.split('\0')))
    assert tracked - set(original) == set(expected_added)
    assert set(original).issubset(tracked), 'deleted tracked file'
    restored = (REPO / SNAPSHOT).read_text()
    for path, rev in revisions.items():
        new = f"'{path}': '{rev['after']}'"
        old = f"'{path}': '{rev['before']}'"
        assert restored.count(new) == 1
        restored = restored.replace(new, old)
    assert restored == original_snapshot, 'unreviewed snapshot edit'
    report.update({'commits':commits,'tree':command(['git','rev-parse','HEAD^{tree}'],REPO).stdout.strip(),
                   'review_branch':BRANCH,'changed_existing':sorted(changed),
                   'added':sorted(expected_added),'unchanged_existing':len(original)-len(changed),
                   'reviewed_snapshot_updates':revisions})
    (OUT / 'report.json').write_text(json.dumps(report,indent=2))
    (OUT / 'candidate.patch').write_text(command(['git','diff',BASE,'HEAD'],REPO).stdout)
    command(['git','format-patch','--output-directory',str(OUT),BASE+'..HEAD'],REPO)
    (OUT / 'candidate-files.json').write_text(json.dumps({p:digest(p) for p in tracked},indent=2))
    command(['git','push','origin',f'HEAD:refs/heads/{BRANCH}'],REPO)
    print('VALIDATED_REVIEW_CANDIDATE',json.dumps(report,indent=2),flush=True)


command(['git','fetch','--depth=1','origin',BASE])
command(['git','worktree','add','--detach',str(REPO),BASE])
assert command(['git','rev-parse','HEAD'],REPO).stdout.strip() == BASE
original = {p:digest(p) for p in filter(None,command(['git','ls-files','-z'],REPO).stdout.split('\0'))}
original_snapshot = (REPO / SNAPSHOT).read_text()
revisions = {}
(OUT / 'baseline-manifest.json').write_text(json.dumps(original,indent=2))
focused = [EXISTING, 'addons/acm_extended/tools/test_historical_chest_workspace.py',
           'addons/acm_extended/tools/test_menu_death_lifecycle.py']
before_rc, before, before_counts = pytest('focused-before', focused)
expected_failure = next(k for k in before if k[1] == 'test_unload_clears_matching_continuous_action_and_pose')
assert before_rc == 1 and {k for k,v in before.items() if v != 'passed'} == {expected_failure}
root_before_rc, root_before, root_before_counts = pytest('root-before', ['tools'])

(REPO / NEW).write_text(TEST)
old_rc, old_control, old_counts = pytest('unchanged-source-control', [NEW])
assert old_rc == 1 and old_counts == {'passed':15,'failed':10,'error':0,'skipped':0}, old_counts
old_log = (OUT / 'unchanged-source-control.log').read_text()
assert 'wrong-generation provider exit' in old_log
assert '[ERR]' not in old_log and '[FAT]' not in old_log

# Batch A changes one final handoff guard, not the authored animation choreography.
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
revise_snapshot(SOURCE)
after_rc, after, after_counts = pytest('focused-after', focused + [NEW])
assert after_rc == 0 and set(after.values()) == {'passed'}
assert set(before).issubset(after) and all(after[k] == 'passed' for k in before)
assert pytest('preservation-A', [SNAPSHOT])[0] == 0
assert record('hemtt', [os.environ['HEMTT'],'check'],150) == 0
report = {'baseline':BASE,'focused_before':before_counts,'focused_after':after_counts,
          'old_source_control':old_counts,'root_before':root_before_counts,
          'hemtt_exit':0,'full_addon_suite_rerun':False,
          'original_unresolved_source_contract_index':146,'release_approved':False}
DOC_A = 'docs/audits/2026-09-23-bounded-backlog-A.md'
DOC_B = 'docs/audits/2026-09-23-bounded-backlog-B.md'
(REPO / DOC_A).write_text(f'''# Bounded continuation A: stethoscope provider exit generation

Baseline: `{BASE}` (published batch 14). Separately named to avoid claiming integration of an unavailable, reportedly unpushed batches 15-17 package.

## Confirmed defect

Stethoscope Unload guarded continuous-action teardown but not its final `headElevMedicSeq` lower request. A superseded display could issue that provider exit over a newer continuous action. The captured continuous-action generation now gates the final request as well. Do not substitute the stethoscope pose epoch: an active Flip legitimately advances the roll pose within the same scope session.

Only that final guard changes runtime. Normal Putdown/inventory/crouch choreography, speed release, Flip cancellation, supine requests, carrier/dead-patient equipment routing, cursor, audio, medication and physiology code remain unchanged.

One existing stethoscope test assertion now expects the current four-argument `treatmentPoseStop` handoff (`true`) instead of requiring the obsolete generic exit. Its identity and other assertions remain. This is contract reconciliation, not a second gameplay defect.

## Validation

The complete actual Unload SQF executes in 25 new cases through the existing SQF-VM harness. Unchanged runtime: {json.dumps(old_counts)}. Candidate: all 25 pass. Cases include missing/stale/current generations, independent pose epochs, ordinary/active-Flip exit, absent/present carrier handoffs, live/dead patients, and provider locality, vehicle, consciousness, life and existing-sequence exclusions.

Focused before: {json.dumps(before_counts)}. Focused after: {json.dumps(after_counts)}. Existing chest-workspace and menu-lifecycle execution modules remain included. HEMTT check returns 0, retaining seven nonblocking suggestions. The preservation test module also passes after one explicitly reviewed digest update for the changed runtime file. No test body is removed and no skip/xfail added. Raw commands, outputs, JUnit identities and before/after manifests are retained in the Actions evidence artifact.

## Boundaries

These tests record calls across explicit engine fixtures. They do not render an Arma animation or certify real displays, network traffic, hearing gain, patient animation-lease release, carrier-lease identity or stale active-Flip cancellation elsewhere in Unload. The actual gear-restoration algorithm is unchanged; the new tests check its dispatch, not engine inventory behavior. No full historical addon suite was rerun. Do not replace its last published 175-failure aggregate with an inferred count. The 146-entry original source-contract index is unchanged. No stable-release approval.
''')
commit_a = commit([SOURCE,EXISTING,NEW,SNAPSHOT,DOC_A], 'Guard stethoscope provider exit by continuous generation (bounded A)')
preserve_and_publish({'A':commit_a}, [SOURCE,EXISTING,SNAPSHOT], [NEW,DOC_A])

# Batch B retains every root assertion and updates only the explicit anterior-up call.
replace_once(ROOT_TEST,
    "assert '[_patient] call ACME_fnc_patientRollCancel;' in steth_close",
    "assert '[_patient,\"front\"] call ACME_fnc_patientRollCancel;' in steth_close")
revise_snapshot(ROOT_TEST)
assert record('phase150-direct',[sys.executable,ROOT_TEST],30) == 0
root_after_rc, root_after, root_after_counts = pytest('root-after',['tools'])
removed = set(root_before) - set(root_after)
assert len(removed) == 1 and all('test_fork_phase150_flip_cancel' in ' '.join(k) and root_before[k] == 'error' for k in removed), removed
assert set(root_after).issubset(root_before)
assert all(root_after[k] == root_before[k] for k in root_after), 'root outcome regression'
assert root_after_rc == root_before_rc == 1
report['root_after'] = root_after_counts
(REPO / DOC_B).write_text(f'''# Bounded continuation B: explicit supine Flip-cancel contract

Parent: `{commit_a}`.

The root phase-150 script required the obsolete one-argument patientRollCancel call. Runtime already requests `[patient, "front"]` to preserve the required supine exit. Only that assertion changes; every other assertion is retained. Batch A's full-Unload execution cases verify the actual anterior-up request during active Flip and the ordinary no-Flip controls. No runtime change in this batch.

The script now executes successfully. Entire root-tools probe before: {json.dumps(root_before_counts)}. After: {json.dumps(root_after_counts)}. Only the phase-150 collection error disappears. All other comparable root outcomes remain unchanged; both commands still return 1. Remaining root errors are open, not waived.

The root script's preservation digest is explicitly updated. Only the two reviewed snapshot cases, for this root script and Batch A's runtime, normalize their digest-valued parameter label for identity comparison; the complete original JUnit labels remain in evidence. Every other protected digest remains untouched. No new skip or xfail is introduced.

The separate historical addon-suite aggregate and original source-contract ledger are unchanged in this bounded pass. No Arma client, dedicated server or release package was run or approved.
''')
commit_b = commit([ROOT_TEST,SNAPSHOT,DOC_B], 'Align root flip-cancel test with explicit supine request (bounded B)')
preserve_and_publish({'A':commit_a,'B':commit_b}, [SOURCE,EXISTING,SNAPSHOT,ROOT_TEST], [NEW,DOC_A,DOC_B])
