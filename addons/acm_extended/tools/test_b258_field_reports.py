"""B258: nine community field reports — first bounded clinical/ownership fixes.

Executed SQF checks use test_menu_death_lifecycle's controlled mock engine;
Arma/ACE multiplayer behavior remains a dedicated-server acceptance task.
"""
from pathlib import Path

from test_menu_death_lifecycle import adapt, execute

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent
F = ROOT / "functions"


def source(name):
    return (F / ("fn_" + name + ".sqf")).read_text(encoding="utf-8-sig")


def test_native_tube_and_explicit_bilateral_presence_are_read_dynamically():
    code = adapt(source("thoraHasTube"))
    execute("ACME_fnc_thoraHasTube={" + code + "};" + r"""
        _patient setVariable ["ACM_breathing_Thoracostomy_State",2];
        [[_patient] call ACME_fnc_thoraHasTube,"native-only historic tube was hidden"] call _check;
        _patient setVariable ["ACME_thora_tube_left",true];
        [[_patient] call ACME_fnc_thoraHasTube,"in-situ left tube was hidden"] call _check;
        _patient setVariable ["ACME_thora_tube_left",false];
        [!([_patient] call ACME_fnc_thoraHasTube),"removed tube remained suctionable from native aggregate"] call _check;
        _patient setVariable ["ACME_thora_tube_right",true];
        [[_patient] call ACME_fnc_thoraHasTube,"remaining right tube lost access"] call _check;
        _patient setVariable ["ACME_thora_tube_right",false];
        [!([_patient] call ACME_fnc_thoraHasTube),"bilateral tube removal kept suction access"] call _check;
    """)


def test_tube_presence_is_checked_at_menu_and_patient_owner_completion():
    menu = (ADDONS/"breathing/ACE_Medical_Treatment_Actions.hpp").read_text()
    drain = (ADDONS/"breathing/functions/fnc_Thoracostomy_drain.sqf").read_text()
    local = (ADDONS/"breathing/functions/fnc_Thoracostomy_drainLocal.sqf").read_text()
    assert 'call ACME_fnc_thoraHasTube' in menu
    assert 'call ACME_fnc_thoraHasTube' in drain
    assert 'call ACME_fnc_thoraHasTube' in local
    assert local.index("thoraHasTube") < local.index("Hemothorax_Fluid")
    assert 'class thoraHasTube {};' in (ROOT/"config.cpp").read_text()


def test_final_tube_removal_retires_native_aggregate_and_definitive_outlet():
    src = source("thoraSideStateCommit")
    block = src.split("if (_wasTube",1)[1]
    assert 'ACME_thora_tube_left' in block and 'ACME_thora_tube_right' in block
    assert '[_patient, [["thoracostomyState", _native]], true]' in block
    assert '_patient setVariable [_tractKey, "split", true];' in block
    assert '[_patient, "tubeRemoved"] call ACME_fnc_ptxTreat;' in block
    assert '_wasTube && {_hasValue}' in src


def test_needle_decompression_has_higher_residual_than_patent_thoracostomy():
    src=source("ptxTreat")
    assert 'case "ncd": {_s set [5,1];_relief=true;};' in src
    assert 'if (_op=="ncd" && {_hadPtx}) then {' in src
    assert '(_s select 8) max 0.85' in src
    assert '(_s select 8) min 0.5' in src
    assert 'case "tubeRemoved": {' in src
    assert '(_s select 8) max 0.75' in src
    assert '(_s select 2) > 0.000001' in src


def test_hpmk_cannot_be_prepped_or_wrapped_during_reserved_cpr():
    cached=(ADDONS/"core/overrides/fnc_canTreatCached.sqf").read_text()
    wrap=source("hpmkWrap")
    prep=source("hpmkPrep")
    for s in [cached,wrap,prep]:
        assert 'ACM_circulation_CPR_Medic' in s
        assert 'ace_medical_CPR_provider' in s
    assert 'ACME_PrepHPMK", "ACME_WrapHPMK' in cached
    assert 'ACME_supplySettle' in prep


def test_awake_obstruction_and_ett_allow_assessment_suction():
    s=(ADDONS/"airway/ACE_Medical_Treatment_Actions.hpp").read_text()
    check=s.split("class CheckAirway: CheckPulse",1)[1].split("class HeadTurn",1)[0]
    suction=s.split("class UseSuctionBag: CheckAirway",1)[1].split("class UseAccuvac",1)[0]
    assert "ACME_ETT_Inserted" in check
    for name in ("AirwayObstructionVomit_State","AirwayObstructionBlood_State"):
        assert name in check and name in suction
    assert 'class UseAccuvac: UseSuctionBag' in s


def test_arrest_pupils_override_is_description_only():
    s=source("tbiAssessPupils")
    assert 'ace_medical_inCardiacArrest' in s
    assert 'if (_patient getVariable ["ace_medical_inCardiacArrest", false] && {_pupils < 2})' in s
    assert 'Pupils: bilaterally sluggish/nonreactive during cardiac arrest.' in s
    assert 'setVariable ["ACME_tbi_State"' not in s


def test_plasma_only_preload_is_insufficient_to_clear_arrest():
    src=(ADDONS/"circulation/functions/fnc_roscEligibility.sqf").read_text()
    assert 'GET_BLOOD_VOLUME(_patient)' in src
    assert 'QGVAR(Blood_Volume)' in src
    assert 'ACME_rosc_minBloodCarryingVolume' in src
    assert 'INSUFFICIENT BLOOD / OXYGEN CAPACITY' in src


def test_parked_carriers_cleanup_is_deletion_not_death():
    src=source("registerManualPlateCarrierRuntime")
    block=src.split('// B258: a parked carrier',1)[1].split('/* Stable B183',1)[0]
    assert '["CAManBase", "Deleted",' in block
    for v in ('ACME_chestAccess_vestProp','ACME_CS_vestProp','ACME_carrierCargo'):
        assert v in block
    assert 'deleteVehicle _prop;' in block
    killed=src.split('["CAManBase", "Killed",',1)[1].split('}] call CBA_fnc_addClassEventHandler',1)[0]
    assert 'deleteVehicle' not in killed
