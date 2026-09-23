from pathlib import Path
import ast,json,re

def identity(row):
    context=row.get('context','')
    if context in ('',"''",'""'):context=''
    match=re.fullmatch(r'SubtestContext\(msg=(.*?), kwargs=(.*)\)',context)
    if match:
        try:context=json.dumps([ast.literal_eval(match[1]),ast.literal_eval(match[2])],sort_keys=True,default=str)
        except (ValueError,SyntaxError):pass
    return (row['nodeid'],row['kind'],row.get('when'),row.get('type'),context)

def compare(folder):
    reports={label:[json.loads(s) for s in (folder/(label+'.jsonl')).read_text().splitlines()] for label in ('before','after')}
    before={identity(r):r for r in reports['before']};after={identity(r):r for r in reports['after']}
    fixed=[k for k in before.keys()&after.keys() if before[k]['outcome']=='failed' and after[k]['outcome']=='passed']
    regress=[k for k in before.keys()&after.keys() if before[k]['outcome']=='passed' and after[k]['outcome']!='passed']
    missing=list(before.keys()-after.keys());newfails=[k for k in after.keys()-before.keys() if after[k]['outcome']=='failed']
    errors={l:[r for r in rs if r['kind']=='collection' or (r.get('when') in ('setup','teardown') and r['outcome']=='failed')] for l,rs in reports.items()}
    return {'fixed_count':len(fixed),'fixed':sorted(k[0] for k in fixed),'regressions':regress,'missing':missing,'new_failures':newfails,'errors':errors,'skips':{l:sum(r['outcome']=='skipped' for r in rs) for l,rs in reports.items()},'broad_remains_failing':True}
