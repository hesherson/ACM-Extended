from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CIRC=ROOT/'addons/circulation'
EXT=ROOT/'addons/acm_extended/functions'
prep=(CIRC/'XEH_PREP.hpp').read_text()
owner=(CIRC/'functions/fnc_setRuntimeState.sqf').read_text()
ui=(CIRC/'functions/fnc_setLocalUiState.sqf').read_text()
assert 'PREP(setRuntimeState);' in prep
assert 'PREP(setLocalUiState);' in prep
for token in [
    'CardiacArrest_PFH','ReversibleCardiacArrest_PFH','AED_Pads_LastSync','AED_Pads_Display','IV_Bags_Active',
    'FluidBagsFlow_IV','FluidBagsFlow_IO','IV_Placement','Cardiac_RhythmState','Blood_Volume','Overload_Volume',
    'Saline_Volume','AED_EKGRhythm','AED_Charged','AED_InUse','AED_Medic_InUse','AED_LastShock','AED_ShockTotal',
    'AED_Analyze_Busy','AED_AnalyzeRhythm_State','CardiacArrest_ResistChecked','CardiacArrest_ShockResistant',
    'AED_NIBP_Display','BloodType','ROSC_Time']:
    assert token in owner,token
for token in ['TransfusionMenu_SelectIV','TransfusionMenu_Selected_BodyPart','TransfusionMenu_Selected_AccessSite','MedicationVialList','SyringeDraw_InventorySelection']:
    assert token in ui,token
viol=[]
for p in EXT.glob('*.sqf'):
    for line in p.read_text().splitlines():
        if 'setVariable ["ACM_circulation_' in line:
            viol.append((p.name,'direct',line.strip()))
        if 'missionNamespace setVariable ["ACM_circulation_' in line:
            viol.append((p.name,'mission',line.strip()))
        if 'ACME_fnc_setVarNet' in line and 'ACM_circulation_' in line:
            viol.append((p.name,'setVarNet',line.strip()))
        if 'setVariable [_x' in line and 'ACM_circulation_' in line:
            viol.append((p.name,'dynamic',line.strip()))
assert not viol,viol
# IV_Bags remains on its dedicated Extended/native bridge rather than the generic circulation writer.
for p in EXT.glob('*.sqf'):
    for line in p.read_text().splitlines():
        assert not ('ACM_circulation_IV_Bags' in line and ('setVariable' in line or 'ACME_fnc_setVarNet' in line)),(p.name,line.strip())
for required in [
    'fn_clearAllAilments.sqf','fn_rhythmThresholdTick.sqf','fn_aedBeatClockTick.sqf','fn_resumeSiteFlow.sqf',
    'fn_ivEnforceSite.sqf','fn_rhythmSet.sqf','fn_edemaSet.sqf','fn_yFlushTick.sqf',
    'fn_arrestLocal.sqf','fn_toggleOverResus.sqf','fn_shockLocal.sqf','fn_circHandle.sqf','fn_respawnClinicalReset.sqf',
    'fn_initBlastOverpressureRuntime.sqf','fn_restorePausedFlow.sqf','fn_registerRoscBreathingRuntime.sqf','fn_openFromTransfusionMenu.sqf','fn_ventDriveTick.sqf']:
    assert 'ACM_circulation_fnc_setRuntimeState' in (EXT/required).read_text(),required
from current_source_contracts import _has
respawn=(EXT/'fn_registerRhythmLifecycleRuntime.sqf').read_text()
assert _has(respawn, '[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;')
assert _has(respawn, '[_u, _issuedAt] call ACME_fnc_respawnClinicalReset;')
for required in ['fn_initMedicationRegistry.sqf','fn_restoreMedicationList.sqf','fn_vialHolder.sqf']:
    assert 'ACM_circulation_fnc_setLocalUiState' in (EXT/required).read_text(),required

# EJ is only a thin selector wrapper. The common access selector owns the native circulation UI state.
ej=(EXT/'fn_selectEJTransfusionSite.sqf').read_text()
select_access=(EXT/'fn_selectTransfusionAccess.sqf').read_text()
assert 'ACME_fnc_selectTransfusionAccess' in ej
assert 'ACM_circulation_fnc_setLocalUiState' in select_access
for required in ['fn_yFlushTick.sqf','fn_clinicalBagMove.sqf','fn_infusionRemoveLocal.sqf']:
    assert 'ACME_fnc_ivBagsCommit' in (EXT/required).read_text(),required
print('fork phase 52 circulation state ownership checks: PASS')

# Junctional bleed now publishes only ACME_junctionalBleedLPS. The native circulation integrator consumes that
# owner-local rate inside getBloodVolumeChange, so this worker must not write native circulation state itself.
junc=(EXT/'fn_junctionalStartBleed.sqf').read_text()
assert 'ACME_junctionalBleedLPS' in junc
assert 'ACM_circulation_fnc_setRuntimeState' not in junc
