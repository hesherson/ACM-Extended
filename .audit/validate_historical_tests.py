"""Independent, hash-gated validation of the reviewed test-maintenance patch.

This worker can publish only a new isolated audit branch after validation.
It never updates main and refuses every production-source or asset change.
The historical suite is expected to remain red; its failures are recorded, not hidden.
"""
from pathlib import Path
import collections
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET

PREP = Path.cwd()
BASE = '19d01b8b27fd53bb9d3c381c7445add589336159'
EXPECTED_TREE = '1ad34b9fe086786c31a8154f236e732bdd105432'
EXPECTED_PATCH = 'df018bb6eda3a58bb314d9670ef4130c9dd5df695018183a0a0c2aa04f992c79'
DEST = Path('/tmp/backlog-candidate')
BEFORE = Path('/tmp/backlog-base')
OUT = Path('/tmp/backlog-validation-results')
OUT.mkdir(exist_ok=True)
DOCS = {'docs/audits/2026-09-22-historical-backlog-batch1.md',
        'docs/audits/2026-09-22-historical-backlog-batch1.json'}


def git(*args, cwd=PREP):
    return subprocess.check_output(['git', *args], cwd=cwd)


def allowed(path):
    return (path.startswith('addons/acm_extended/tools/') and path.endswith('.py')
            and '..' not in Path(path).parts) or path in DOCS


def run(args, cwd, label, expected_code=0, timeout=480):
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    (OUT / (label + '.log')).write_text(p.stdout)
    print(label, 'exit', p.returncode, flush=True)
    print(p.stdout[-3500:], flush=True)
    assert p.returncode == expected_code, (label, p.returncode)
    return p


def stats(xml):
    root = ET.parse(xml).getroot()
    suites = list(root.iter('testsuite'))
    result = {key:sum(int(s.get(key, '0')) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    result['passed_xml_outcomes'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    return result


def outcomes(xml):
    result = collections.defaultdict(list)
    for case in ET.parse(xml).getroot().iter('testcase'):
        key = (case.get('classname', ''), case.get('name', ''))
        state = 'failure' if case.find('failure') is not None else 'error' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        result[key].append(state)
    return result


# Validate the transparent transferred text before touching the candidate worktree.
parts = [PREP / f'.audit/historical-tests-{i:02d}.patch' for i in range(16)]
payload = b''.join(p.read_bytes() for p in parts)
actual_patch = hashlib.sha256(payload).hexdigest()
print('Patch bytes:', len(payload), 'SHA256:', actual_patch, flush=True)
(OUT / 'transfer-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in parts}, indent=2))
assert actual_patch == EXPECTED_PATCH, 'Transferred patch differs from reviewed local bytes'
patch = OUT / 'historical-tests.patch'
patch.write_bytes(payload)
entries = git('apply', '--numstat', str(patch)).decode().splitlines()
assert len(entries) == 53, len(entries)
for line in entries:
    add, delete, path = line.split('\t', 2)
    assert add.isdecimal() and delete.isdecimal() and allowed(path), line

subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', BASE], check=True)
subprocess.run(['git', 'worktree', 'add', '--detach', str(DEST), BASE], check=True)
subprocess.run(['git', 'worktree', 'add', '--detach', str(BEFORE), BASE], check=True)
subprocess.run(['git', 'apply', '--check', str(patch)], cwd=DEST, check=True)
subprocess.run(['git', 'apply', '--index', str(patch)], cwd=DEST, check=True)
assert git('write-tree', cwd=DEST).decode().strip() == EXPECTED_TREE
changed = git('diff', '--cached', '--name-status', cwd=DEST).decode().splitlines()
assert len(changed) == 53
for row in changed:
    status, path = row.split('\t', 1)
    assert status in ('A', 'M') and allowed(path), row
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=DEST, check=True)
(OUT / 'production-preservation.json').write_text(json.dumps({
    'base':BASE, 'candidate_tree':EXPECTED_TREE, 'production_or_asset_changes':0,
    'deleted_files':0, 'changed_paths':changed, 'patch_sha256':actual_patch}, indent=2))

# Previously passing preservation and lifecycle suite plus the reviewed green backlog groups.
modules = ['test_consciousness_wake_latch_20260921.py', 'test_seizure_paralysis_suppression.py',
    'test_seizure_gesture_unification.py', 'test_debug_seizure_action.py', 'test_bvm_startup.py',
    'test_iv_ui_followup_patch.py', 'test_wake_execution_20260922.py', 'test_config_compile.py',
    'test_confirmed_lifecycle_20260922.py', 'test_historical_source.py', 'test_b17_release.py',
    'test_b18_ventway.py', 'test_b19_vials_pea_artifact.py', 'test_b21_rhythm_sync.py',
    'test_b27_junctional_cpr_bvm.py', 'test_b29_narc_plunger.py', 'test_b29_svt_contract.py',
    'test_b34_procedure_access.py', 'test_b35_lifecycle.py', 'test_b35_treatments.py',
    'test_b91_ace_interaction_postinit.py']
focused = ['tools/test_self_audit_20260922.py'] + ['addons/acm_extended/tools/' + p for p in modules]
run(['python3', '-m', 'pytest', *focused, '-q', '--junitxml=' + str(OUT / 'focused.xml')], DEST, 'focused')
focused_stats = stats(OUT / 'focused.xml')
assert focused_stats == {'tests':786, 'failures':0, 'errors':0, 'skipped':0, 'passed_xml_outcomes':786}, focused_stats

# Full runs intentionally retain historical failure reporting and do not suppress failing assertions.
common = ['python3', '-m', 'pytest', 'addons/acm_extended/tools', '--continue-on-collection-errors', '-q', '--tb=line']
run([*common, '--ignore=addons/acm_extended/tools/test_b77_branding_authors.py',
     '--junitxml=' + str(OUT / 'baseline.xml')], BEFORE, 'baseline', expected_code=1)
run([*common, '--junitxml=' + str(OUT / 'candidate.xml')], DEST, 'candidate', expected_code=1)
base_stats, candidate_stats = stats(OUT / 'baseline.xml'), stats(OUT / 'candidate.xml')
assert base_stats == {'tests':5019, 'failures':460, 'errors':12, 'skipped':4, 'passed_xml_outcomes':4543}, base_stats
assert candidate_stats == {'tests':8312, 'failures':354, 'errors':0, 'skipped':4, 'passed_xml_outcomes':7954}, candidate_stats
old, new = outcomes(OUT / 'baseline.xml'), outcomes(OUT / 'candidate.xml')
regressions = [key for key, states in new.items() if 'failure' in states
               and 'passed' in old.get(key, []) and not any(x in old.get(key, []) for x in ('failure','error'))]
assert not regressions, regressions
run([os.environ['HEMTT'], 'check'], DEST, 'hemtt', timeout=240)
assert git('write-tree', cwd=DEST).decode().strip() == EXPECTED_TREE
assert git('diff', '--name-only', cwd=DEST).decode().strip() == '', 'Test run modified tracked files'
summary = {'base':BASE, 'candidate_tree':EXPECTED_TREE, 'focused':focused_stats,
           'baseline':base_stats, 'candidate':candidate_stats,
           'newly_failing_previous_passes':regressions, 'production_or_asset_changes':0,
           'hemtt_check_exit':0, 'full_suite_clean':False,
           'limits':'SQF-VM uses engine-boundary mocks; no Arma client or dedicated server was executed.'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2), flush=True)

# Publish only the verified test/doc tree to a NEW audit branch. Main is never written here.
env = {**os.environ, 'GIT_AUTHOR_NAME':'mavis',
       'GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com',
       'GIT_COMMITTER_NAME':'mavis', 'GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit = subprocess.check_output(['git', 'commit-tree', EXPECTED_TREE, '-p', BASE, '-m',
    'Repair historical test infrastructure and verify outstanding contracts without runtime changes'], cwd=DEST, env=env, text=True).strip()
branch = 'audit/historical-backlog-tests-20260922'
existing = git('ls-remote', '--heads', 'origin', 'refs/heads/' + branch)
assert not existing.strip(), 'Candidate publication branch already exists; refusing to overwrite it'
subprocess.run(['git', 'push', 'origin', commit + ':refs/heads/' + branch], cwd=PREP, check=True)
(OUT / 'candidate-commit.json').write_text(json.dumps({'commit':commit, 'tree':EXPECTED_TREE, 'parent':BASE, 'branch':branch}, indent=2))
print('Verified test-only candidate:', commit, 'main unchanged', flush=True)
