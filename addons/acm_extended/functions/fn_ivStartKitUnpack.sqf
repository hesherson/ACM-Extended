/* Convert physical kits only on their carrier. Overlapping pickup and loadout
 * events can run this again safely because each grant requires a fresh debit. */
params ["_unit",["_pickedUp",""]];
if (isNull _unit || {!local _unit} || {!alive _unit} || {is3DEN}
    || {_unit isEqualTo (missionNamespace getVariable ["ace_arsenal_center",objNull])}) exitWith {0};
private _kits = (items _unit) select {
    (_x find "ACME_IVStartKit_") == 0 && {_pickedUp == "" || {_x == _pickedUp}}
};
if (_kits isEqualTo []) exitWith {0};
if (_unit getVariable ["ACME_persistenceFrozen",false]) exitWith {
    if !(_unit getVariable ["ACME_ivStartKitDeferred",false]) then {
        _unit setVariable ["ACME_ivStartKitDeferred",true];
        [{
            params ["_unit"];
            isNull _unit || {!local _unit} || {!(_unit getVariable ["ACME_persistenceFrozen",false])}
        },{
            params ["_unit"];
            if (isNull _unit) exitWith {};
            _unit setVariable ["ACME_ivStartKitDeferred",false];
            [_unit] call ACME_fnc_ivStartKitUnpack;
        },[_unit]] call CBA_fnc_waitUntilAndExecute;
    };
    0
};

private _unpacked = 0;
isNil {
    {
        private _kit = _x;
        private _catheter = getText (configFile >> "CfgWeapons" >> _kit >> "ACME_ivKitCatheter");
        if (_catheter != "") then {
            private _receipt = [_unit,_unit,[_kit],true] call ACME_fnc_treatmentSupplyTake;
            if (_receipt isNotEqualTo [] && {[_receipt,false] call ACME_fnc_treatmentSupplyRefund}) then {
                {
                    [_unit,_x] call ace_common_fnc_addToInventory;
                } forEach [_catheter,"ACME_NARBOA","ACME_Tegaderm","ACME_SalineLock","ACME_IVExtension","ACME_IVLine","ACM_SalineFlush_10"];
                _unpacked = _unpacked + 1;
            };
        };
    } forEach _kits;
};
_unpacked
