from historical_source import read_source
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT/rel, errors='ignore')

def test_b44_version():
    s=txt('config.cpp')+txt('functions/fn_postInit.sqf')
    assert '1.0.100-r8' in s

def test_roll_provider_emptyhand_wrapper():
    c=txt('config.cpp'); f=txt('functions/fn_rollProviderStart.sqf')
    assert 'class ACME_RollProviderWork: AinvPknlMstpSnonWrflDr_medic2_old' in c
    block=c.split('class ACME_RollProviderWork:',1)[1].split('};',1)[0]
    for x in ['disableWeapons = 1','disableWeaponsLong = 1','disableWeaponsShort = 1','disableReload = 1','canPullTrigger = 0']:
        assert x in block
    assert '"AmovPknlMstpSnonWnonDnon", 0.15' in block
    assert '"ACME_RollProviderWork"' in f
    assert 'selectWeapon ""' in f
    assert 'setUnitPos "MIDDLE"' in f
    assert '2.5' in f

def test_chest_seal_flip_patient_roll():
    f=txt('functions/fn_chestSealFlip.sqf')
    r=txt('functions/fn_chestSealRoll.sqf')
    assert 'ACME_fnc_chestSealRoll' in f
    assert 'ACME_fnc_rollProviderStart' in f
    assert 'owner' in f or 'remoteExec' in f
    assert 'rolltofront' in r and 'rolltoback' in r
    assert ', 2] call ACME_fnc_doAnim' in r or ',2] call ACME_fnc_doAnim' in r

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
    s=txt('functions/fn_airwayInjuryRelabel.sqf')
    assert 'airway is patent' in s
    for x in ['NPA','OPA','iGel','Endotracheal Tube']:
        assert x.lower() in s.lower()

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
