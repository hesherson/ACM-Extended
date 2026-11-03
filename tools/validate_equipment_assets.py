"""Check imported addon prefixes and all literal local model/material/texture references."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    addons={p.name:p for p in (Path(root)/'addons').glob('acme_*') if p.is_dir()}
    failures=[];count=0
    for name,p in addons.items():
        if (p/'$PBOPREFIX$').read_text().strip()!=name:failures.append(f'{name}: prefix mismatch')
        for f in p.rglob('*'):
            if f.suffix.lower() not in ('.cpp','.cfg','.rvmat'):continue
            for ref in re.findall(r'"([^"\r\n]*\.(?:p3d|paa|rvmat))"',f.read_text(),re.I):
                parts=[x for x in ref.replace('\\','/').split('/') if x]
                if not parts or parts[0] not in addons:continue
                count+=1
                target=addons[parts[0]].joinpath(*parts[1:])
                if not target.is_file():failures.append(f'{f.relative_to(root)}: {ref}')
    assert not failures,'\n'.join(failures)
    print(f'Equipment references: {count} resolved across {len(addons)} runtime addons')
    return count

if __name__=='__main__':validate()
