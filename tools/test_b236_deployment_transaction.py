"""Real filesystem transactions/fault injection; no claim of Windows/Arma execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

spec = importlib.util.spec_from_file_location('b236_deploy', Path(__file__).with_name('deploy_acme_release.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

@pytest.fixture
def setup(tmp_path):
    release = tmp_path / 'release'; (release/'addons').mkdir(parents=True); (release/'keys').mkdir()
    (release/'keys'/'test.bikey').write_bytes(b'public-key-fixture')
    for name in m.PBO_NAMES:
        (release/'addons'/name).write_bytes(b'new-pbo-'+name.encode())
        (release/'addons'/(name+'.test.bisign')).write_bytes(b'signature-fixture')
    (release/'mod.cpp').write_text('new mod config')
    targets = [tmp_path/'installed', tmp_path/'installed/.hemttout/build']
    for target in targets:
        (target/'addons/source/functions').mkdir(parents=True)
        (target/'addons/source/functions/keep.sqf').write_text('source must survive')
        for file in m.artifacts(release):
            dst=target/file.relative_to(release); dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(b'OLD:'+file.read_bytes())
    keys = tmp_path/'server keys'; keys.mkdir(); (keys/'unrelated.bikey').write_bytes(b'keep trust')
    root=tmp_path/'journal'
    return release,targets,root,keys

def snapshot(targets):
    return {str(p):p.read_bytes() for target in targets for p in target.rglob('*') if p.is_file() and not p.name.endswith('.tmp')}

def test_complete_two_targets_and_separate_key(setup):
    release,targets,root,keys=setup
    result=m.deploy(release,targets,root,keys)
    assert result['state']=='VERIFIED' and not (root/'active.json').exists()
    for target in targets:
        for p in m.artifacts(release): assert (target/p.relative_to(release)).read_bytes()==p.read_bytes()
        assert (target/'addons/source/functions/keep.sqf').read_text()=='source must survive'
    assert (keys/'test.bikey').read_bytes()==(release/'keys/test.bikey').read_bytes()
    assert (keys/'unrelated.bikey').read_bytes()==b'keep trust'

@pytest.mark.parametrize('name',['ACM_retired.pbo','other_mod.pbo','OLD.PBO'])
def test_rejects_extra_active_pbos_without_any_mutation(setup,name):
    release,targets,root,keys=setup
    (targets[1]/'addons'/name).write_bytes(b'retired'); before=snapshot(targets)
    with pytest.raises(m.DeployError,match='Extra active'):m.deploy(release,targets,root)
    assert snapshot(targets)==before
    assert not (root/'active.json').exists()

@pytest.mark.parametrize('phase,index',[('stage',0),('stage',29),('replace',0),('replace',1),('replace',30),('replace',59),('replace',60),('verify',61)])
def test_failure_restores_both_targets_and_key(setup,phase,index):
    release,targets,root,keys=setup
    (keys/'test.bikey').write_bytes(b'OLD KEY')
    before=snapshot(targets+[keys])
    def fault(p,i):
        if (p,i)==(phase,index):raise OSError('injected disk/copy failure')
    with pytest.raises(OSError,match='injected'):m.deploy(release,targets,root,keys,hook=fault)
    assert snapshot(targets+[keys])==before
    assert not (root/'active.json').exists()
    assert not list(targets[0].rglob('*.tmp'))

@pytest.mark.parametrize('missing',['key','signature','pbo'])
def test_incomplete_release_rejected(setup,missing):
    release,targets,root,_=setup;before=snapshot(targets)
    p=next((release/'keys').iterdir()) if missing=='key' else next((release/'addons').glob('*.bisign' if missing=='signature' else '*.pbo'))
    p.unlink()
    with pytest.raises((m.DeployError,FileNotFoundError)):m.deploy(release,targets,root)
    assert snapshot(targets)==before

def test_private_key_rejected(setup):
    release,targets,root,_=setup;(release/'private.biprivatekey').write_bytes(b'never distribute')
    with pytest.raises(m.DeployError,match='Private'):m.deploy(release,targets,root)

def test_mismatched_copied_file_rolls_back(setup,monkeypatch):
    release,targets,root,_=setup;before=snapshot(targets);original=m.shutil.copy2
    def damaged(source,destination,*args,**kwargs):
        r=original(source,destination,*args,**kwargs)
        if str(destination).endswith('.tmp'):Path(destination).write_bytes(b'corrupt')
        return r
    monkeypatch.setattr(m.shutil,'copy2',damaged)
    with pytest.raises(m.DeployError,match='Copy verification'):m.deploy(release,targets,root)
    assert snapshot(targets)==before

def test_abrupt_process_death_blocks_deploy_until_recovery(setup):
    release,targets,root,keys=setup;before=snapshot(targets+[keys])
    code='''import importlib.util,sys,os\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location("deploy",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\ndef fault(p,i):\n if p=="replace" and i==31:os._exit(91)\nm.deploy(Path(sys.argv[2]),[Path(sys.argv[3]),Path(sys.argv[4])],Path(sys.argv[5]),Path(sys.argv[6]),hook=fault)\n'''
    result=subprocess.run([sys.executable,'-c',code,str(Path(m.__file__)),str(release),*[str(t) for t in targets],str(root),str(keys)],timeout=30)
    assert result.returncode==91 and (root/'active.json').exists()
    with pytest.raises(m.DeployError,match='Unfinished'):m.deploy(release,targets,root)
    m.recover(root)
    assert snapshot(targets+[keys])==before and not (root/'active.json').exists()

def test_concurrent_edit_preserves_recovery_required_state(setup):
    release,targets,root,_=setup
    def fault(p,i):
        if p=='verify':
            (targets[0]/'mod.cpp').write_text('UNRELATED CONCURRENT EDIT')
            raise OSError('fail final check')
    with pytest.raises(m.DeployError,match='Rollback incomplete'):m.deploy(release,targets,root,hook=fault)
    assert (targets[0]/'mod.cpp').read_text()=='UNRELATED CONCURRENT EDIT'
    assert json.loads((root/'active.json').read_text())['state']=='RECOVERY_REQUIRED'

def test_symlink_destination_refused(setup,tmp_path):
    release,targets,root,_=setup
    p=targets[0]/'addons';outside=tmp_path/'outside';p.rename(outside)
    try:p.symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('Host does not permit symlinks')
    with pytest.raises(m.DeployError,match='Redirected'):m.deploy(release,targets,root)

def test_os_lock_prevents_overlapping_transaction(setup):
    release,targets,root,_=setup
    with m.exclusive(root):
        with pytest.raises(m.DeployError,match='Another deployment'):m.deploy(release,targets,root)

def test_new_artifacts_are_removed_during_rollback_without_deleting_source(setup):
    release,targets,root,_=setup
    for t in targets:
        for p in m.artifacts(release):(t/p.relative_to(release)).unlink()
    before=snapshot(targets)
    def fault(p,i):
        if p=='replace' and i==35:raise OSError('new install fault')
    with pytest.raises(OSError):m.deploy(release,targets,root,hook=fault)
    assert snapshot(targets)==before


@pytest.mark.parametrize('existing', [False, True])
def test_failure_after_receipt_does_not_leave_false_success(setup,existing):
    release,targets,root,_=setup
    previous={'id':'previous-run','state':'VERIFIED'}
    if existing:m.write_json(root/'last-success.json',previous)
    before=snapshot(targets)
    def fault(phase,index):
        if phase=='receipt':raise OSError('receipt fault')
    with pytest.raises(OSError,match='receipt fault'):m.deploy(release,targets,root,hook=fault)
    assert snapshot(targets)==before
    assert json.loads((root/'last-success.json').read_text())==previous if existing else not (root/'last-success.json').exists()


def test_release_change_after_validation_rejected_before_replacement(setup):
    release,targets,root,_=setup
    manifest={p.relative_to(release).as_posix():m.digest(p) for p in m.artifacts(release)}
    next((release/'addons').glob('*.pbo')).write_bytes(b'changed after signature validation')
    before=snapshot(targets)
    with pytest.raises(m.DeployError,match='changed after'):m.deploy(release,targets,root,expected_manifest=manifest)
    assert snapshot(targets)==before
    assert not (root/'active.json').exists()


def test_copy_flushes_a_write_capable_handle_for_windows(tmp_path,monkeypatch):
    source=tmp_path/'source';target=tmp_path/'target';source.write_bytes(b'contents')
    modes={};original_open=Path.open;original_sync=m.os.fsync
    def opened(path,mode='r',*args,**kwargs):
        f=original_open(path,mode,*args,**kwargs);modes[f.fileno()]=mode;return f
    def synced(fd):
        mode=modes.get(fd,'')
        assert '+' in mode or 'w' in mode or 'a' in mode,'Windows requires GENERIC_WRITE for FlushFileBuffers'
        original_sync(fd)
    monkeypatch.setattr(Path,'open',opened);monkeypatch.setattr(m.os,'fsync',synced)
    m._copy_verified(source,target,m.digest(source))
    assert target.read_bytes()==source.read_bytes()
