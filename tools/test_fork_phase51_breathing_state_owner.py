from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BREATH=ROOT/'addons/breathing'
EXT=ROOT/'addons/acm_extended/functions'
prep=(BREATH/'XEH_PREP.hpp').read_text()
owner=(BREATH/'functions/fnc_setRuntimeState.sqf').read_text()
assert 'PREP(setRuntimeState);' in prep
for token in [
    'RespirationRate','BVM_provider','BVM_ConnectedOxygen','BVM_lastBreath','BVM_lastBreathOxygen',
    'Thoracostomy_UsedKit','Thoracostomy_State','Hemothorax_Fluid','ChestSeal_State','Pneumothorax_PFH','Stethoscope_LungState',
    'Pneumothorax_State','TensionPneumothorax_State','TensionPneumothorax_Time','Hardcore_Pneumothorax','Hemothorax_State']:
    assert token in owner,token
# No Extended function may publish ACM breathing state directly or through ACME's generic network writer.
viol=[]
for p in EXT.glob('*.sqf'):
    for line in p.read_text().splitlines():
        if 'setVariable ["ACM_breathing_' in line:
            viol.append((p.name,'direct',line.strip()))
        if 'ACME_fnc_setVarNet' in line and 'ACM_breathing_' in line:
            viol.append((p.name,'setVarNet',line.strip()))
    # Catch same-line dynamic mixed-key writers that still carry a native breathing key.
    for line in p.read_text().splitlines():
        if 'setVariable [_x' in line and 'ACM_breathing_' in line:
            viol.append((p.name,'dynamic-list',line.strip()))
assert not viol,viol
callers=[p.name for p in EXT.glob('*.sqf') if 'ACM_breathing_fnc_setRuntimeState' in p.read_text()]
for required in [
    'fn_clinicalReset.sqf','fn_megacodeSetAirway.sqf','fn_megacodeScenarioTick.sqf','fn_megacodeSetVital.sqf',
    'fn_ventManualBreathCommit.sqf','fn_ventHardStopCommit.sqf','fn_ventSimpleManualBreath.sqf','fn_ventPatientClear.sqf','fn_ventDriveTick.sqf',
    'fn_thoraAftercareLocal.sqf','fn_thoraDrainBloodLocal.sqf','fn_thoraPassiveDrain.sqf','fn_chestSealEffectLocal.sqf','fn_ptxEnsure.sqf','fn_ptxPublish.sqf',
    'fn_toggleOverResus.sqf','fn_megacodeChestInjury.sqf']:
    assert required in callers,(required,callers)
print('fork phase 51 breathing state ownership checks: PASS')

# Finger widening is a provider request; only the owner may register the tract or drain fluid.
thora_ui=(EXT/'fn_thoraMouseDown.sqf').read_text()
thora_request=(EXT/'fn_thoraAftercareRequest.sqf').read_text()
assert 'ACME_fnc_thoraAftercareRequest' in thora_ui and 'ACME_fnc_ownerDispatch' in thora_request
assert 'ACM_breathing_fnc_setRuntimeState' not in thora_ui
for name in ('fn_thoraAftercareLocal.sqf','fn_thoraDrainBloodLocal.sqf'):
    assert '!local _patient' in (EXT/name).read_text(),name

# Advanced manual breath UI is request-only; the casualty-owner commit owns native breathing mutation.
manual=(EXT/'fn_ventManualBreath.sqf').read_text()
commit=(EXT/'fn_ventManualBreathCommit.sqf').read_text()
assert '[_patient, "ventManualBreath"' in manual and 'ACME_fnc_ownerDispatch' in manual
assert 'ACM_breathing_fnc_setRuntimeState' in commit

# Hard-stop UI is request/presentation; the patient-owner commit releases native BVM support.
hard_ui=(EXT/'fn_ventStopHard.sqf').read_text()
hard_commit=(EXT/'fn_ventHardStopCommit.sqf').read_text()
assert 'ventHardStop' in hard_ui and 'ACME_fnc_ownerDispatch' in hard_ui
assert 'ACM_breathing_fnc_setRuntimeState' in hard_commit
