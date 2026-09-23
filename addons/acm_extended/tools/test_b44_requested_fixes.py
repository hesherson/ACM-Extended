from historical_source import read_source, assert_release_identity
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT/rel, errors='ignore')

def test_b44_version():
    s=txt('config.cpp')+txt('functions/fn_postInit.sqf')
    assert_release_identity()

def test_roll_provider_emptyhand_wrapper():
    # Preserve the historical identity, not the superseded medic2 wrapper mapping.
    from test_historical_roll_cancellation import test_roll_enters_shared_empty_hand_medic4_with_current_timeline
    from test_historical_pose_lifecycle import test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions
    for stance in ('CROUCH','STAND','PRONE'):
        test_roll_enters_shared_empty_hand_medic4_with_current_timeline(stance)
    test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions('ACME_RollProviderWork','AinvPknlMstpSnonWnonDnon_medic4',0)
    # Keep the still-applicable weapon and crouch-link checks from the old test.
    cfg = txt('config.cpp')
    wrapper = cfg.split('class ACME_RollProviderWork:',1)[1].split('};',1)[0]
    for property in ('disableWeapons = 1','disableWeaponsLong = 1','disableWeaponsShort = 1','disableReload = 1','canPullTrigger = 0'):
        assert property in wrapper
    assert 'connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15' in wrapper

def test_chest_seal_flip_patient_roll():
    # Route through the patient owner and preserve a priority-one lease, with the
    # existing token-scoped priority-two graph repair only if the transition fails.
    from test_historical_chest_workspace import (
        test_roll_uses_priority_one_lease_then_only_a_scoped_fallback_and_requested_rest,
        test_same_side_request_is_a_noop_and_nonlocal_request_is_forwarded,
    )
    assert 'ACME_fnc_rollProviderStart' in txt('functions/fn_chestSealFlip.sqf')
    for target,transition,hold in (
        ('front','AinjPpneMstpSnonWrflDnon_rolltoback','ACM_LyingState'),
        ('back','AinjPpneMstpSnonWrflDnon_rolltofront','ace_medical_engine_uncon_anim_1')):
        for started in (False,True):
            test_roll_uses_priority_one_lease_then_only_a_scoped_fallback_and_requested_rest(target,transition,hold,started)
        test_same_side_request_is_a_noop_and_nonlocal_request_is_forwarded(target)

def test_death_is_hard_reset_boundary():
    p=txt('functions/fn_postInit.sqf'); c=txt('functions/fn_clearAllAilments.sqf')
    assert 'ACME_fnc_clearAllAilments' in p
    assert 'private _preserveDeathInterventions = false' in c
    assert 'if (_preserveDeathInterventions) exitWith' not in c
    assert 'ACME_CS_reset' in c
    assert 'ACME_IV_Marks' in c
    assert '"incision"' in c

def test_dead_assessment_exceptions():
    s=txt('overrides/fn_canTreatCached.sqf')
    for x in ['CheckAirway','CheckBreathing','UseStethoscope','ACME_InspectChest']:
        assert x in s
    for x in ['RemoveOPA','RemoveNPA','RemoveIGel','ACME_Extubate']:
        assert x in s

def test_close_holes_independent_seals():
    m=txt('functions/fn_chestSealMouseDown.sqf'); g=txt('functions/fn_chestSealGenHoles.sqf')
    assert 'ACME_CS_minHoleSep' in g
    assert re.search(r'ACME_CS_minHoleSep"\s*,\s*0', g)
    assert 'open' in m.lower() and 'hole' in m.lower()

def test_airway_patent_suffix():
    # Current device labels show placement only. Patency belongs to Check Airway;
    # do not restore an automatic patent label from a device's mere presence.
    from test_historical_laryngoscopy_execution import test_airway_device_rows_do_not_disclose_unassessed_patency
    for selection in (0,1):
        for inserted in (False,True):
            for alive in (False,True):
                test_airway_device_rows_do_not_disclose_unassessed_patency(selection,inserted,alive)

def test_airway_menu_order_and_tab():
    c=txt('functions/fn_postInit.sqf'); u=txt('overrides/fn_updateActions.sqf')
    m=re.search(r'ACME_menuGroups\s*=.*?\[\s*\"adjuncts\".*?\[(.*?)\]', c, re.S|re.I)
    assert m
    b=m.group(1)
    assert b.find('Check Airway') < b.find('Perform Head Turning') < b.find('Perform Head Tilt-Chin Lift')
    assert 'Airway / Breathing' in u

def test_head_elevation_no_roll_and_cohesive():
    a=txt('functions/fn_headElevateStart.sqf'); b=txt('functions/fn_headElevApplyTilt.sqf'); e=txt('functions/fn_headElevateStop.sqf')
    joined=a+b+e
    code='\n'.join(line for line in joined.splitlines() if not line.lstrip().startswith('//'))
    assert 'Db_grab' not in code and 'Db_release' not in code
    assert 'rolltofront' not in code.lower() and 'rolltoback' not in code.lower()
    assert 'ACME_fnc_headElevApplyTilt' in a and 'ACME_fnc_headElevMedicStart' in a
    ms=txt('functions/fn_headElevMedicStart.sqf')
    assert 'ACME_fnc_headElevMedicSeq' in ms

def test_no_roll_config_uses_nonnumeric_false():
    c=txt('config.cpp')
    # At least several body actions that explicitly must not invoke ACM's body fallback use string false.
    assert c.count('ACM_rollToBack = "false"') >= 4
