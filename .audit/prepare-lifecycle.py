"""Read-only staging inputs, hash-checked edits in an isolated checkout only."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

BASE = 'c3dd15f41a56a253461d876b478f91849d23551f'
EXPECTED_TREE = '6149f6e098fb4d2334cfec4587dda9c4ee0a8436'
STAGING = Path(__file__).resolve().parent
DEST = Path(sys.argv[1]).resolve()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=DEST)


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe(path):
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('addons', 'tools'):
        raise ValueError('Unexpected candidate path: ' + path)
    f = DEST.joinpath(*p.parts)
    if not f.resolve().is_relative_to(DEST) or f.is_symlink():
        raise ValueError('Unsafe candidate path: ' + path)
    return f


assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert not git('status', '--porcelain'), 'Candidate checkout must start clean'
entries = []
for name in ('lifecycle-edits-0.json', 'lifecycle-edits-1.json'):
    entries.extend(json.loads((STAGING / name).read_text()))
assert len(entries) == 14
paths = [entry['path'] for entry in entries]
assert len(set(paths)) == len(paths)
# Capture all originals before applying any change, including moved presentation code.
originals = {p: safe(p).read_bytes() if safe(p).exists() else b'' for p in paths}
for entry in entries:
    for edit in entry['edits']:
        for segment in edit.get('segments', []):
            if 'copy_path' in segment:
                p = segment['copy_path']
                originals.setdefault(p, safe(p).read_bytes())

staged = {}
for entry in entries:
    path = entry['path']
    data = originals[path]
    base_sha = entry['base_sha']
    if base_sha is None:
        assert not safe(path).exists(), path
    else:
        assert blob(data) == base_sha, ('base mismatch', path, blob(data), base_sha)
    lines = data.decode('utf-8').splitlines(keepends=True)
    edits = entry['edits']
    last = 0
    for edit in edits:
        assert last <= edit['start'] <= edit['end'] <= len(lines), path
        last = edit['end']
    for edit in reversed(edits):
        if 'segments' in edit:
            segments = []
            for segment in edit['segments']:
                if 'copy_path' in segment:
                    source = originals[segment['copy_path']].decode('utf-8').splitlines(keepends=True)
                    assert 0 <= segment['start'] <= segment['end'] <= len(source)
                    segments.append(''.join(source[segment['start']:segment['end']]))
                else:
                    segments.append(segment['text'])
            text = ''.join(segments)
        else:
            text = edit['text']
        lines[edit['start']:edit['end']] = text.splitlines(keepends=True)
    result = ''.join(lines).encode()
    assert blob(result) == entry['expected_sha'], ('result mismatch', path, blob(result), entry['expected_sha'])
    staged[path] = result

new_test = 'addons/acm_extended/tools/test_confirmed_lifecycle_20260922.py'
assert not safe(new_test).exists()
test_bytes = (STAGING / 'test_confirmed_lifecycle_20260922.py').read_bytes()
assert blob(test_bytes) == 'a852d0d7ffcd6249c5caf68a47413973f2fdeac3'
staged[new_test] = test_bytes
assert len(staged) == 15
# All source checks passed before writing any candidate files.
for path, data in staged.items():
    file = safe(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(data)
subprocess.run(['git', 'add', '--', *sorted(staged)], cwd=DEST, check=True)
assert set(git('diff', '--cached', '--name-only').decode().splitlines()) == set(staged)
assert not git('diff', '--cached', '--diff-filter=D', '--name-only')
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=DEST, check=True)
actual = git('write-tree').decode().strip()
assert actual == EXPECTED_TREE, ('complete tree mismatch', actual)
print('BASE:', BASE)
print('VERIFIED COMPLETE TREE:', actual)
print('Changed paths:', len(staged), '(no deletions)')
print('\n'.join(sorted(staged)))
