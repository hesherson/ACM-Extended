"""Retain the completed broad comparison; normalize one test EOF and rerun focused/build checks."""
from pathlib import Path
import hashlib, io, json, os, shutil, urllib.request, zipfile

ROOT=Path('/tmp/acme-ae-af-results')
PRIOR=ROOT/'first-run'; PRIOR.mkdir(parents=True,exist_ok=True)
ARTIFACT=10778924722
EXPECTED='9f4ad7841f81f798cdec13a8035b70b0e1047ab0d1eabde163b1d4a5d6a9b16c'
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        assert newurl.startswith('https://')
        redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
        if redirected is not None: redirected.remove_header('Authorization')
        return redirected
request=urllib.request.Request(f'https://api.github.com/repos/hesherson/ACM-Extended/actions/artifacts/{ARTIFACT}/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
with urllib.request.build_opener(SafeRedirect).open(request,timeout=60) as response:
    raw=response.read()
assert hashlib.sha256(raw).hexdigest()==EXPECTED,'Prior evidence digest mismatch'
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
    archive.extractall(PRIOR)
assert (PRIOR/'diff-check.log').read_text()=='addons/acm_extended/tools/test_b64_syringe_tag_carousel_refinement.py:146: new blank line at EOF.\n'
assert hashlib.sha256((PRIOR/'reviewed.patch').read_bytes()).hexdigest()=='5e3fb6222619f049cdae65e1bf1bda8b6953b9fe3c0d556820d62bb6cbd4a6d7'
source=Path('.audit/ae-af/validate.py').read_text()

def replace(old,new):
    global source
    assert source.count(old)==1,old
    source=source.replace(old,new)

# Broad logs and raw JUnit are reused explicitly, not labelled as newly executed.
old="    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])"
replace(old,"""    if name in {'addon-before','addon-after','root-before','root-after'}:
        shutil.copyfile(PRIOR/(name+'.xml'),xml)
        shutil.copyfile(PRIOR/(name+'.log'),OUT/(name+'.log'))
        print(name,'RETAINED FROM FULL COMPARISON RUN 35927614107; only one test EOF differs',flush=True)
        rc=1
    else:
"""+old.replace('    rc=','        rc=',1))
replace("original=manifest(BEFORE)","original=manifest(BEFORE)\nassert original==json.loads((PRIOR/'baseline-manifest.json').read_text()), 'Different baseline'")
old="git(AFTER,'apply','--check',str(patch));git(AFTER,'apply',str(patch))"
replace(old,old+"""
# The candidate exactly reconstructs the reviewed patch whose complete suites ran above.
# Only surplus terminal newline bytes in this one Python test file are normalized.
repair_path=AFTER/T/'test_b64_syringe_tag_carousel_refinement.py'
old_bytes=repair_path.read_bytes()
new_bytes=old_bytes.rstrip(b'\\n')+b'\\n'
assert old_bytes==new_bytes+b'\\n' and new_bytes.endswith(b'\\n')
assert ast.dump(ast.parse(old_bytes))==ast.dump(ast.parse(new_bytes))
repair_path.write_bytes(new_bytes)
(OUT/'formatting-repair.json').write_text(json.dumps({'path':str(repair_path.relative_to(AFTER)),'before_sha256':hashlib.sha256(old_bytes).hexdigest(),'after_sha256':hashlib.sha256(new_bytes).hexdigest(),'removed_bytes':1,'python_ast_unchanged':True,'runtime_bytes_changed_by_repair':0},indent=2))
""")
old="report['AE']=sha_ae"
replace(old,old+"""
report['broad_comparison_source_run']=35927614107
report['broad_comparison_artifact_sha256']=EXPECTED
report['final_formatting_only_difference']='One extra EOF newline removed from test_b64_syringe_tag_carousel_refinement.py; AST and all runtime bytes unchanged.'
report['fresh_after_formatting']=['original-runtime controls','focused 86 tests','HEMTT check','diff check','complete file preservation']
""")
compile(source,'.audit/ae-af/validate.py','exec')
exec(compile(source,'.audit/ae-af/validate.py','exec'),globals())
