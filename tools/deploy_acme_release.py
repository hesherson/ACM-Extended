#!/usr/bin/env python3
"""Artifact-only, journalled ACME installation. Python 3.9+; no third-party packages.

Never mirrors/removes source directories. Rejects extra active PBOs. Stages and
backs up all artifacts before replacing any. Handled failures roll back; abrupt
termination leaves an active journal that blocks another deploy until recovery.
This is NOT an atomic multi-file swap or a native Arma acceptance test.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Iterator, Optional
import uuid

PBO_NAMES = {f'ACM_{n}.pbo'.casefold() for n in (
    'acm_extended','airway','breathing','cbrn','circulation','core','damage',
    'disability','evacuation','gui','itemtext','main','mission','zeus')}

class DeployError(RuntimeError):
    pass

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def safe_path(path: Path) -> None:
    """Refuse symlinks/junctions in managed paths; never follow a redirected tree."""
    for p in (path, *path.parents):
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise DeployError(f'Redirected path is not supported: {p}')
        # Python 3.9 on Windows: junction detection without Path.is_junction.
        if os.name == 'nt' and p.exists() and getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
            raise DeployError(f'Reparse point is not supported: {p}')

def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)

@contextmanager
def exclusive(root: Path) -> Iterator[None]:
    safe_path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'deploy.lock').open('a+b') as f:
        f.seek(0); f.write(b'0'); f.flush(); f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise DeployError('Another deployment/recovery owns the installation lock.') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def artifacts(release: Path) -> list[Path]:
    safe_path(release)
    if not release.is_dir():
        raise DeployError(f'Release not found: {release}')
    for p in release.rglob('*'):
        safe_path(p)
        if p.suffix.casefold() == '.biprivatekey':
            raise DeployError('Private signing key found in distributable release.')
    pbos = sorted(p for p in (release / 'addons').iterdir() if p.is_file() and p.suffix.casefold() == '.pbo')
    if len(pbos) != 14 or {p.name.casefold() for p in pbos} != PBO_NAMES:
        raise DeployError('Release must contain the exact 14 ACME PBO names (no extras/duplicates).')
    keys = list((release / 'keys').glob('*.bikey'))
    if len(keys) != 1:
        raise DeployError('Release must contain exactly one public signing key.')
    signatures = [p.with_name(p.name + '.' + keys[0].stem + '.bisign') for p in pbos]
    files = pbos + signatures + keys + sorted(p for p in release.iterdir() if p.is_file())
    for p in files:
        if not p.is_file() or p.stat().st_size == 0:
            raise DeployError(f'Missing/empty artifact: {p}')
    allowed = {p.relative_to(release) for p in files}
    # Do not silently ignore unexpected release content in active artifact directories.
    for sub in ('addons', 'keys'):
        for p in (release / sub).iterdir():
            if not p.is_file() or p.relative_to(release) not in allowed:
                raise DeployError(f'Unexpected release artifact: {p}')
    names = [str(p.relative_to(release)).casefold() for p in files]
    if len(set(names)) != len(names):
        raise DeployError('Case-insensitive artifact-name collision.')
    return files

def target_preflight(target: Path) -> None:
    safe_path(target)
    folder = target / 'addons'
    if not folder.exists():
        return
    if not folder.is_dir():
        raise DeployError(f'Addon path is not a directory: {folder}')
    actual = [p for p in folder.iterdir() if p.suffix.casefold() == '.pbo']
    extras = [p.name for p in actual if p.name.casefold() not in PBO_NAMES]
    if extras:
        raise DeployError(f'Extra active PBOs at {folder}: {", ".join(sorted(extras))}. Nothing removed; review and move them outside the mod folder.')
    if len({p.name.casefold() for p in actual}) != len(actual):
        raise DeployError(f'Duplicate case-insensitive PBO names at {folder}')
    for p in actual:
        safe_path(p)
        if not p.is_file():
            raise DeployError(f'Non-file PBO entry: {p}')

def _copy_verified(source: Path, target: Path, expected: str) -> None:
    safe_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    # Windows FlushFileBuffers requires a write-capable handle. Do not fsync
    # a read-only reopened descriptor even though that happens to work on Linux.
    with target.open('r+b') as f:
        os.fsync(f.fileno())
    if digest(target) != expected:
        raise DeployError(f'Copy verification failed: {target}')

def _journal_entries(journal: dict, root: Path) -> list[dict]:
    if journal.get('schema') != 1 or not re.fullmatch(r'[0-9a-f]{32}', journal.get('id', '')):
        raise DeployError('Invalid recovery journal. Preserve it for manual review.')
    run = root / journal['id']
    entries = journal.get('entries')
    if not isinstance(entries, list):
        raise DeployError('Invalid journal entries.')
    for e in entries:
        dest, backup, stage = Path(e['destination']), Path(e['backup']), Path(e['stage'])
        base = Path(e['target']); rel = Path(e['relative'])
        if rel.is_absolute() or '..' in rel.parts or dest != base / rel:
            raise DeployError('Invalid journal destination.')
        if stage != dest.with_name('.' + dest.name + '.acme-' + journal['id'] + '.tmp'):
            raise DeployError('Invalid staging path in journal.')
        if not backup.is_relative_to(run):
            raise DeployError('Invalid backup path in journal.')
        for p in (dest, backup, stage):
            safe_path(p)
    return entries

def _rollback(journal: dict, root: Path) -> None:
    """Restore intent-recorded files; refuse to overwrite unrelated concurrent edits."""
    entries = _journal_entries(journal, root)
    errors = []
    for e in reversed(entries):
        if not e.get('intent'):
            continue
        dest = Path(e['destination']); backup = Path(e['backup']); stage = Path(e['stage'])
        try:
            current = digest(dest) if dest.is_file() else None
            if current not in (e['old_hash'], e['new_hash'], None):
                raise DeployError(f'File changed outside this transaction: {dest}')
            if e['old_hash'] is not None:
                if not backup.is_file() or digest(backup) != e['old_hash']:
                    raise DeployError(f'Original backup missing/damaged: {backup}')
                _copy_verified(backup, stage, e['old_hash']); os.replace(stage, dest)
                if digest(dest) != e['old_hash']:
                    raise DeployError(f'Rollback hash mismatch: {dest}')
            elif dest.exists():
                dest.unlink()  # Only a new artifact explicitly recorded by this transaction.
            e['intent'] = False
            write_json(root / 'active.json', journal)
        except BaseException as exc:
            errors.append(str(exc))
    if errors:
        journal['state'] = 'RECOVERY_REQUIRED'; journal['recovery_errors'] = errors
        write_json(root / 'active.json', journal)
        raise DeployError('Rollback incomplete. DO NOT LAUNCH. Backups/journal retained: ' + '; '.join(errors))
    for e in entries:
        Path(e['stage']).unlink(missing_ok=True)
    # A receipt written just before a crash must not describe files we rolled back.
    previous = journal.get('previous_success')
    success = root / 'last-success.json'
    if previous is None:
        if success.exists() and json.loads(success.read_text(encoding='utf-8')).get('id') == journal['id']:
            success.unlink()
    else:
        write_json(success, previous)
    journal['state'] = 'ROLLED_BACK'
    write_json(root / journal['id'] / 'result.json', journal)
    (root / 'active.json').unlink()

def recover(root: Path) -> None:
    with exclusive(root):
        active = root / 'active.json'
        if not active.is_file():
            raise DeployError('No unfinished deployment journal exists.')
        _rollback(json.loads(active.read_text(encoding='utf-8')), root)

def deploy(release: Path, targets: list[Path], root: Path,
           server_keys: Optional[Path] = None,
           hook: Optional[Callable[[str, int], None]] = None,
           expected_manifest: Optional[dict[str, str]] = None) -> dict:
    """hook is test-only fault injection, never exposed by the command-line interface."""
    release = release.absolute(); targets = [p.absolute() for p in targets]; root = root.absolute()
    if len(set(targets)) != len(targets) or not targets:
        raise DeployError('Targets must be nonempty and distinct.')
    with exclusive(root):
        if (root / 'active.json').exists():
            raise DeployError('Unfinished deployment detected. DO NOT LAUNCH; run recovery first.')
        files = artifacts(release)
        hashes = {p.relative_to(release).as_posix(): digest(p) for p in files}
        if expected_manifest is not None and hashes != expected_manifest:
            raise DeployError('Release changed after signature/identity validation. Revalidate before deploying.')
        for target in targets:
            if target == release or target.is_relative_to(release):
                raise DeployError('Release cannot be an installation target.')
            target_preflight(target)
        if server_keys:
            server_keys = server_keys.absolute(); safe_path(server_keys)
            if not server_keys.is_dir():
                raise DeployError('Separate server keys directory does not exist.')
        ident = uuid.uuid4().hex
        success = root / 'last-success.json'
        journal = dict(schema=1, id=ident, state='PREPARING', entries=[],
                       previous_success=json.loads(success.read_text(encoding='utf-8')) if success.exists() else None)
        seen = set()
        pairs = [(src, target, src.relative_to(release)) for target in targets for src in files]
        if server_keys:
            pairs += [(src, server_keys, Path(src.name)) for src in files if src.suffix == '.bikey']
        for i, (src, target, rel) in enumerate(pairs):
            dest = target / rel
            safe_path(dest)
            if dest in seen:  # Optional server keys can coincide with the installed keys folder.
                continue
            seen.add(dest)
            if dest.exists() and not dest.is_file():
                raise DeployError(f'Artifact destination is not a file: {dest}')
            # Case-only names on case-sensitive filesystems must not create two active PBOs.
            if dest.parent.is_dir() and any(p.name.casefold() == dest.name.casefold() and p.name != dest.name for p in dest.parent.iterdir()):
                raise DeployError(f'Case-only destination mismatch: {dest}')
            journal['entries'].append(dict(source=str(src), target=str(target), relative=str(rel),
                destination=str(dest), backup=str(root / ident / 'backup' / str(i)),
                stage=str(dest.with_name('.' + dest.name + '.acme-' + ident + '.tmp')),
                old_hash=digest(dest) if dest.is_file() else None, new_hash=hashes[src.relative_to(release).as_posix()], intent=False))
        write_json(root / 'active.json', journal)
        try:
            for i, e in enumerate(journal['entries']):
                if hook: hook('stage', i)
                if e['old_hash'] is not None:
                    _copy_verified(Path(e['destination']), Path(e['backup']), e['old_hash'])
                _copy_verified(Path(e['source']), Path(e['stage']), e['new_hash'])
            journal['state'] = 'REPLACING'; write_json(root / 'active.json', journal)
            for i, e in enumerate(journal['entries']):
                if hook: hook('replace', i)
                # Persist intent before replacement, including for hard-kill recovery.
                e['intent'] = True; write_json(root / 'active.json', journal)
                os.replace(e['stage'], e['destination'])
                if digest(Path(e['destination'])) != e['new_hash']:
                    raise DeployError(f'Installed hash mismatch: {e["destination"]}')
            if hook: hook('verify', len(journal['entries']))
            for target in targets:
                target_preflight(target)
            for e in journal['entries']:
                if digest(Path(e['destination'])) != e['new_hash']:
                    raise DeployError(f'Final verification failed: {e["destination"]}')
            journal['state'] = 'VERIFIED'; write_json(root / ident / 'result.json', journal)
            # The receipt is committed only after both target sets and the optional key pass.
            write_json(root / 'last-success.json', {k:v for k,v in journal.items() if k != 'previous_success'})
            if hook: hook('receipt', len(journal['entries']))
            (root / 'active.json').unlink()
            return journal
        except BaseException:
            _rollback(journal, root)
            raise

def verify_release(release: Path, hemtt: str, commit: str) -> dict[str, str]:
    files = artifacts(release)
    manifest = {p.relative_to(release).as_posix(): digest(p) for p in files}
    key = next(p for p in files if p.suffix == '.bikey')
    for p in files:
        if p.suffix.casefold() != '.pbo':
            continue
        args = [hemtt, 'utils', 'pbo', 'inspect', str(p), '--format', 'json', '--no-color']
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        props = result.stdout.split('Checksum (SHA1)', 1)[0]
        if result.returncode or re.findall(r'^\s*- git:\s*(\S+)\s*$', props, re.M) != [commit] or re.findall(r'^\s*- version:\s*(\S+)\s*$', props, re.M) != ['1.2.4.1']:
            raise DeployError(f'Packaged source/version identity mismatch: {p.name}')
        result = subprocess.run([hemtt, 'utils', 'verify', str(p), str(key), '--no-color'],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        if result.returncode:
            raise DeployError(f'Signature verification failed: {p.name}\n{result.stdout}')

    if manifest != {p.relative_to(release).as_posix(): digest(p) for p in artifacts(release)}:
        raise DeployError('Release changed during signature/identity verification.')
    return manifest

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['deploy','preflight','recover'])
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--server-keys', type=Path)
    parser.add_argument('--hemtt', default='hemtt')
    a = parser.parse_args(argv)
    try:
        repo = a.repo.absolute(); safe_path(repo)
        gitdir = subprocess.check_output(['git','rev-parse','--absolute-git-dir'], cwd=repo, text=True).strip()
        root = Path(gitdir) / 'acme-deploy'; targets = [repo, repo / '.hemttout/build']
        if a.operation == 'recover':
            recover(root); print('Previous artifact set restored. Rebuild/redeploy before using the new source.'); return 0
        if a.operation == 'preflight':
            with exclusive(root):
                if (root / 'active.json').exists():
                    raise DeployError('Unfinished transaction: recover before building/deploying.')
                for target in targets: target_preflight(target)
            print('Destination preflight passed. No artifacts changed.'); return 0
        commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=repo, text=True).strip()
        release = repo / '.hemttout/release'
        manifest = verify_release(release, a.hemtt, commit)
        result = deploy(release, targets, root, a.server_keys, expected_manifest=manifest)
        print(f'ACME artifact deployment VERIFIED: {len(result["entries"])} files; journal {root / "last-success.json"}')
        print('Native Arma/dedicated-server acceptance has NOT been performed by this tool.')
        return 0
    except (DeployError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f'DEPLOYMENT FAILED: {exc}', file=sys.stderr); return 1

if __name__ == '__main__':
    raise SystemExit(main())
