"""B266: stale owner packets cannot consume a replacement kit's new preparation."""
from test_menu_death_lifecycle import execute
from test_b265_equipment_transactions import weapon_setup
from test_b266_kit_boundary import kit_code


def test_old_owner_restore_packet_cannot_take_new_kit_preparation_snapshot():
    execute(weapon_setup()+kit_code()+r'''
        private _localUnit=true;
        _medic setVariable ["ACME_hang_Start",10];
        [_medic] call ACM_core_fnc_equipmentKitChanged;
        // A new preparation has captured fresh-kit weapons but its new
        // patient claim/active episode has not started yet.
        _medic setVariable ["ACME_hang_weaponKitEpoch",1];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
        private _before=str _loadout;
        [!([_medic,10] call ACME_fnc_hangBagRestoreWeapons),"old owner packet consumed newer kit preparation"] call _check;
        [str _loadout==_before && {_adds==0},"old packet restored new preparation weapons"] call _check;
        [(_medic getVariable ["ACME_hang_savedWeaponSlots",[]]) isEqualTo [_rifle,[]],"old packet settled new kit custody"] call _check;
    ''')
