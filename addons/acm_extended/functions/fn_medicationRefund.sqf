/* Provider-local inventory settlement. Called once per acknowledged escrow record.
   [magazines [[class,ammo]], virtual drawn records, empty items returned on success].
   Missing ACK is NOT a refund: an already delivered dose may merely have a delayed reply. */
params ["_medic", ["_payload",[]], ["_accepted",false]];
if (isNull _medic || {!local _medic} || {_payload isEqualTo []}) exitWith {};
_payload params [["_mags",[]],["_drawn",[]],["_successItems",[]],["_supplyReceipts",[]]];
{[_x,!_accepted] call ACME_fnc_treatmentSupplyRefund;} forEach _supplyReceipts;
if (_accepted) exitWith {
    {[_medic,_x] call ace_common_fnc_addToInventory;} forEach _successItems;
};
{_x params ["_class","_ammo"]; _medic addMagazine [_class,_ammo];} forEach _mags;
if !(_drawn isEqualTo []) then {
    private _store = +(_medic getVariable ["ACME_narcStore",[]]);
    {_store pushBack (+_x);} forEach _drawn;
    [_medic, _store] call ACME_fnc_narcStoreCommit;
    if (_medic isEqualTo ACE_player) then {
        [_medic] call ACME_fnc_skStoreEnsureIds;
        if (!isNull (findDisplay 84000)) then {call ACME_fnc_skRefreshDrawn;};
    };
};
