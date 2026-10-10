"""Physical syringe preparation conserves source, item ammo and saved-row volume.

Run native preparation and the actual scheduled draw-success callback. Engine
inventory/UI are captured boundaries; vial accounting and rounding are real SQF.
"""
import re

import pytest

from test_historical_medication_preparation import prep_code, transaction_setup
from test_menu_death_lifecycle import ROOT, execute, read


def native(name):
    return (ROOT / 'addons/circulation/functions' / ('fnc_' + name + '.sqf')).read_text()


def button_code():
    text = native('Syringe_Draw_Button')
    text = re.sub(r'(_\w+) displayCtrl (?:_\w+|\d+)', 'objNull', text)
    text = re.sub(r'ctrlText _\w+', '"Draw"', text)
    text = text.replace('localize (format ["STR_ACM_Circulation_Medication_%1", _medication])', '_medication')
    text = text.replace('localize "STR_ACM_Circulation_Syringe_Drawn"', '"Drew %1"')
    text = re.sub(r'playSound "[^"]+";', '', text)
    return prep_code(text)


def setup():
    return (transaction_setup() + '''
        private _magazines=[];
        ace_common_fnc_addToInventory={_magazines pushBack _this;};
        ACME_fnc_skPendingTagCommit={}; ACME_fnc_skApplyPendingTag={_this select 0};
        ACME_fnc_skRefreshDrawn={}; ACME_fnc_skAfterSaveOpenBody={};
    ''' + 'ACM_circulation_fnc_Syringe_PrepareFinish={' + prep_code(native('Syringe_PrepareFinish')) + '};' +
        'private _drawButton={' + button_code() + '};')


def reserve_code():
    # Preserve Hardcore's actual class/ammo selection and rejection. Only engine cargo
    # reads/writes are replaced; this catches a row whose rounding cannot find its item.
    text = read('hardcorePushStart').split('private _magClass = "";', 1)[1].split('private _serial =', 1)[0]
    text = 'private _magClass = "";' + text
    text = text.replace('magazinesAmmoCargo _x', '_physicalMagazines')
    text = text.replace('uniformContainer ACE_player', 'missionNamespace')
    text = text.replace('vestContainer ACE_player', 'objNull').replace('backpackContainer ACE_player', 'objNull')
    text = text.replace('_magContainer addMagazineAmmoCargo [_magClass,-1,_ammo];', '_reserved pushBack [_magClass,-1,_ammo];')
    return prep_code(text)


@pytest.mark.parametrize('dose,ammo', [(1.237,124), (1.231,123), (0.004,0)])
def test_native_draw_callback_saves_same_volume_as_physical_item_and_source(dose, ammo):
    execute(setup() + f'''
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACM_circulation_SyringeDraw_Size=10;
        ACM_circulation_SyringeDraw_DrawnAmount={dose};
        [0] call _drawButton;
        [count _waits==1,"native draw callback was not scheduled"] call _check;
        ((_waits select 0) select 1) call ((_waits select 0) select 0);
        private _store=_medic getVariable ["ACME_narcStore",[]];
        [count _store=={int(ammo>0)} && {{count _magazines=={int(ammo>0)}}},"row/item count differs or zero-volume syringe created"] call _check;
        [abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-(20-{ammo}/100))<0.000001,
            "source debit does not match physical syringe"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")=={int(ammo==0)},"zero draw consumed a barrel or successful draw retained it"] call _check;
    ''' + (f'''
        private _row=_store select 0;
        [abs ((_row select 2)-{ammo}/100)<0.000001,"saved row retained unrepresentable precision"] call _check;
        [((_magazines select 0) select 3)=={ammo},"physical syringe has wrong ammo"] call _check;
        private _drug=_row select 2;private _size=_row select 1;private _med=_row select 0;private _virtual=false;
        private _physicalMagazines=_magazines apply {{[_x select 1,_x select 3]}};
        private _reserved=[];
        private _reserve={{''' + reserve_code() + '''true};
        [call _reserve,"saved syringe cannot be selected for Hardcore push"] call _check;
        [count _reserved==1,"physical syringe was not reserved exactly once"] call _check;
    ''' if ammo else ''))


@pytest.mark.parametrize('dose,size', [(0,10), (-1,10), (0.004,10), (11,10), (2,1)])
def test_invalid_or_unrepresentable_native_preparation_preserves_supplies(dose, size):
    execute(setup() + f'''
        _inventoryCounts set ["ACM_Syringe_{size}",1];
        private _result=[_medic,"Ketamine",{dose},{size}] call ACM_circulation_fnc_Syringe_PrepareFinish;
        [!_result,"invalid volume accepted"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"invalid preparation consumed solution"] call _check;
        [count _magazines==0 && {{(_inventoryCounts get "ACM_Syringe_{size}")==1}},"invalid preparation changed syringe inventory"] call _check;
    ''')


def test_failed_barrel_removal_refunds_source_and_does_not_create_filled_item():
    execute(setup() + '''
        private _realTake=ACME_fnc_itemTake;
        ACME_fnc_itemTake={if ((_this select 1)=="ACM_Syringe_10") exitWith {false};_this call _realTake;};
        private _result=[_medic,"Ketamine",1.237,10] call ACM_circulation_fnc_Syringe_PrepareFinish;
        [!_result,"failed barrel reservation accepted"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"failed barrel reservation lost solution"] call _check;
        [count _magazines==0 && {(_inventoryCounts get "ACM_Syringe_10")==1},"failed barrel reservation duplicated item"] call _check;
    ''')
