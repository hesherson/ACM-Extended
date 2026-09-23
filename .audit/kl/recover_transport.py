"""Restore two exact transport slips; decoded patch hashes remain authoritative."""
from pathlib import Path
import base64, gzip, hashlib, json
path=Path('.audit/kl/payload.json')
data=json.loads(path.read_text())
fixes={'K':[(2797,2798,'b','')], 'L':[(271,271,'','k+Kl')]}
for label,edits in fixes.items():
    wire=data[label]['gzip']
    for start,end,old,new in reversed(edits):
        assert wire[start:end]==old, (label,'unexpected transport bytes')
        wire=wire[:start]+new+wire[end:]
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==data[label]['sha256'], label+' decoded patch differs'
    data[label]['gzip']=wire
path.write_text(json.dumps(data,separators=(',',':')))
print('Exact original locally tested patch bytes restored and verified.')
