"""Expose original native control constructors to historical UI fixtures.

The disabled decorative frame is an engine-rendering boundary in these fixtures.
B295's dedicated tests execute the production factory, verify paint-before-hit
ordering and require unchanged native class/IDC/parent and code outside it.
"""
from source_scan import lex, matching, split_args

def native_controls(source):
    ts=lex(source);pairs=matching(ts);edits=[]
    for i,t in enumerate(ts):
        if t.value!='ACME_fnc_uiGlassControl' or i<2 or ts[i-1].value!='call':continue
        end=i-2
        assert ts[end].value==']'
        begin=pairs[end];args=split_args(ts,begin+1,end,pairs)
        assert 3<=len(args)<=5
        # Token string lengths exclude quotes; use next token offsets for exact argument bytes.
        values=[]
        for a in args:
            first=a[0];last=a[-1]
            if first.kind=='string' and len(a)==1:values.append('"'+first.value.replace('"','""')+'"')
            else:values.append(' '.join(x.value for x in a))
        native=values[1:3]
        if len(values)>=4 and values[3]!='controlNull':native.append(values[3])
        edits.append((ts[begin].offset,t.offset+len(t.value),values[0]+' ctrlCreate ['+','.join(native)+']'))
    for a,b,value in reversed(edits):source=source[:a]+value+source[b:]
    return source
