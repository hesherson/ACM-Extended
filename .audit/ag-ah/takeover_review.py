"""Apply the reviewed startup-lock addition to the staged AG audit before execution."""
from pathlib import Path
import hashlib

root=Path(__file__).resolve().parent
patch_addition='''diff --git a/addons/acm_extended/functions/fn_skInject.sqf b/addons/acm_extended/functions/fn_skInject.sqf
index eaf1ebe..84180e6 100644
--- a/addons/acm_extended/functions/fn_skInject.sqf
+++ b/addons/acm_extended/functions/fn_skInject.sqf
@@ -9,6 +9,21 @@ private _display = findDisplay 84000;
 if (isNull _display) exitWith {};
 if (!isNull (_display displayCtrl 84130)) exitWith {};  // already injected on this instance.
 
+// A fresh injected workspace replaces any display-bound normal push before it takes
+// ownership of the shared UI flags. Do not inherit an abandoned injection lock.
+private _previousPush = uiNamespace getVariable ["ACME_SK_NormalPush",[]];
+if (count _previousPush >= 5) then {
+    uiNamespace setVariable ["ACME_SK_NormalPush",[]];
+    private _hcPush = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
+    if !(_hcPush isEqualType createHashMap && {count _hcPush > 0}) then {
+        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
+        uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
+        private _oldPushPfh = uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1];
+        if (_oldPushPfh >= 0) then {[_oldPushPfh] call CBA_fnc_removePerFrameHandler;};
+        uiNamespace setVariable ["ACME_SK_PushAnimPFH",-1];
+    };
+};
+
 // Each injected display owns one teardown generation. Older/repeated Unload events
 // must not mutate the shared preparation state of a replacement display.
 private _closeEpoch = (uiNamespace getVariable ["ACME_SK_CloseEpoch", 0]) + 1;
'''
extra_tests=r'''

@pytest.mark.parametrize('started', [False,True])
@pytest.mark.parametrize('hardcore', [False,True])
def test_registration_retires_inherited_normal_locks_before_new_workspace(started,hardcore):
    execute(setup() + 'call ACME_fnc_skConfirmInjection;' + ('0 call _runWait;' if started else '') + ("""
        missionNamespace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["flowing",true]]];
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",99];
    """ if hardcore else '') + """
        _drawDisplay=parsingNamespace; _removed=[];call _register;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[1]]) isEqualTo [],"registration inherited obsolete normal job"] call _check;
    """ + f"""
        [(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]) isEqualTo {str(hardcore).lower()},"registration inherited a dead normal lock or stopped Hardcore"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselBusy",false]) isEqualTo {str(hardcore).lower()},"registration inherited carousel lock or stopped Hardcore"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])=={99 if hardcore else -1},"wrong inherited PFH retirement"] call _check;
        [_removed isEqualTo {'[0]' if started and not hardcore else '[]'},"registration removed the wrong handler"] call _check;
    """ + ("""
        uiNamespace setVariable ["ACME_SK_PendingInjection",["rightleg",2,"vascular"]];
        [call ACME_fnc_skConfirmInjection,"successor remained stuck behind old lock"] call _check;
    """ if not hardcore else ''))
'''
# Restore the identical triple-single-quoted test bytes used in the local proof.
extra_tests=extra_tests.replace('"""',"'''" )
p=root/'workspace.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='75434a2483b75a09661722ea744d73f07590ea45fcb8d608ea28a1e83a4b27bd'
p.write_text(p.read_text()+extra_tests)
assert hashlib.sha256(p.read_bytes()).hexdigest()=='78f9799fe829ec61f96fd5ec8a39648cb784c198a26f7b21a3b15dacfb7340a6'
p=root/'reviewed.patch'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='7e05bb3297bfebc0645c438ff5cbfad7660077e99e92b5ea88e3dd6f52704b98'
p.write_text(p.read_text()+patch_addition)
patch_hash=hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'validate.py';s=p.read_text()
replacements={
 "'7e05bb3297bfebc0645c438ff5cbfad7660077e99e92b5ea88e3dd6f52704b98'":repr(patch_hash),
 "'75434a2483b75a09661722ea744d73f07590ea45fcb8d608ea28a1e83a4b27bd'":"'78f9799fe829ec61f96fd5ec8a39648cb784c198a26f7b21a3b15dacfb7340a6'",
 "FIXTURE=T+'test_bounded_normal_push_lifetime.py'":"FIXTURE=T+'test_bounded_normal_push_lifetime.py'\nINJECT='addons/acm_extended/functions/fn_skInject.sqf'",
 "EXPECTED={":"EXPECTED={\n INJECT:'af8109d045e43a7208810cb82a95a35a69f9d52209fce9eba103095be3a2fb5e',",
 "{'failed':11,'passed':8}":"{'failed':15,'passed':8}",
 "{'passed':150}":"{'passed':154}",
 "len(added)==54":"len(added)==58",
 "{RUNTIME,FIXTURE,OLD_G,OLD_H,LEDGER}":"{RUNTIME,INJECT,FIXTURE,OLD_G,OLD_H,LEDGER}",
 "'new_passing_cases':54":"'new_passing_cases':58",
 "'runtime_files_changed':[RUNTIME]":"'runtime_files_changed':[RUNTIME,INJECT]",
 "commit([RUNTIME,FIXTURE,NEW_G,DOC_G]":"commit([RUNTIME,INJECT,FIXTURE,NEW_G,DOC_G]",
 "Only skConfirmInjection changes runtime.":"Only skConfirmInjection and skInject change runtime. New display injection retires the previous display-bound job and its inherited locks/PFH before assigning the new workspace generation; Hardcore locks are preserved. This prevents a successor remaining stuck behind an abandoned normal job.",
 "Nineteen actual confirmation/registration/Unload execution cases produce eleven failures and eight passes":"Twenty-three actual confirmation/registration/Unload execution cases produce fifteen failures and eight passes",
 "and unowned registration rejection.":"and unowned registration rejection. Four additional takeover cases verify that a fresh successor can start a push immediately, while persistent Hardcore locks and its handle remain untouched.",
}
for old,new in replacements.items():
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new)
p.write_text(s)
compile(s,str(p),'exec')
print('Reviewed takeover addition:',patch_hash)
