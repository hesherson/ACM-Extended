from pathlib import Path
from runpy import run_path
ROOT=Path(__file__).resolve().parents[1]
POST=(ROOT/"addons/acm_extended/functions/fn_postInit.sqf").read_text()
CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
helpers={
 "registerMedicationDeliveryRuntime":("fn_registerMedicationDeliveryRuntime.sqf","ACME_fnc_medicationRetry"),
 "registerEcgJostleRuntime":("fn_registerEcgJostleRuntime.sqf","ACME_fnc_ecgJostleRequest"),
 "registerSyringeLifecycleRuntime":("fn_registerSyringeLifecycleRuntime.sqf","ACME_fnc_resetPersonalMedicationKit"),
}
for fn,(file,token) in helpers.items():
    text=(ROOT/"addons/acm_extended/functions"/file).read_text()
    assert token in text,(fn,token)
    assert f"class {fn} {{}};" in CFG
    assert f"call ACME_fnc_{fn};" in POST
# B279: death clears selection while retaining tangible stock; respawn owns a new kit.
# Parse handler code rather than accepting function names hidden in comments/strings.
_scan=run_path(str(ROOT/"addons/acm_extended/tools/source_scan.py"))
_lex,_matching,_split_args,_render=(_scan[n] for n in ("lex","matching","split_args","render"))

def _handler_tokens(text,event):
    tokens=_lex(text); pairs=_matching(tokens); handlers=[]
    for i,token in enumerate(tokens[:-1]):
        if token.kind != "ident" or token.value != "addEventHandler" or tokens[i+1].value != "[":continue
        opening=i+1
        arguments=_split_args(tokens,opening+1,pairs[opening],pairs)
        if len(arguments)==2 and len(arguments[0])==1 and arguments[0][0].kind=="string" and arguments[0][0].value==event:
            assert arguments[1][0].value=="{" and arguments[1][-1].value=="}",event
            handlers.append(arguments[1])
    assert len(handlers)==1,(event,"expected one native lifecycle handler")
    return handlers[0]

def _assert_syringe_lifecycle(text):
    killed=_handler_tokens(text,"Killed"); respawn=_handler_tokens(text,"Respawn")
    killed_refs={t.value for t in killed if t.kind=="ident"}
    assert not killed_refs.intersection({"ACME_fnc_narcStoreCommit","ACME_fnc_resetPersonalMedicationKit","ACME_fnc_inventoryLedgerCommit","ACME_fnc_inventoryLedgerSettle"}),"death must preserve transferable corpse stock"
    killed_code=_render(killed)
    for statement in ('uiNamespace setVariable ["ACME_SK_SelectedSyringeId", ""];',
                      'uiNamespace setVariable ["ACME_SK_CarouselIdx", -1];',
                      'uiNamespace setVariable ["ACME_SK_SelDrawn", -1];'):
        assert _render(_lex(statement)) in killed_code,("Killed",statement)
    assert _render(_lex('_unit setVariable ["ACME_narcStore", []')) not in killed_code,"death must not clear the corpse store directly"
    respawn_code=_render(respawn)
    for statement in ('if (isNull _unit || {!local _unit}) exitWith {};',
                      '[_unit] call ACM_core_fnc_equipmentKitChanged;',
                      '[_unit] call ACME_fnc_resetPersonalMedicationKit;'):
        assert _render(_lex(statement)) in respawn_code,("Respawn",statement)

_assert_syringe_lifecycle((ROOT/"addons/acm_extended/functions/fn_registerSyringeLifecycleRuntime.sqf").read_text())

for token in ["ACME_medicationAck","ACME_ecgJostleLeaseSec","ACME_narcStore"]:
    assert token not in POST,token
assert POST.strip().endswith('call ACME_fnc_registerSyringeLifecycleRuntime;')
assert len(POST.splitlines()) < 825, len(POST.splitlines())
print("fork phase 36 delivery/ECG/syringe runtime ownership checks: PASS")
