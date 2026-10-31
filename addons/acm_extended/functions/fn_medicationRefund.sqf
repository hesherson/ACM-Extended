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
    {
        private _returned = +_x;
        private _sid = _returned param [11,"",[""]];
        private _at = if (_sid == "") then {-1} else {_store findIf {(_x param [11,"",[""]]) == _sid}};
        // A measured push can retain the same physical syringe while its ACK is
        // pending. Rejected aliquots rejoin that identity instead of creating a
        // second tagged syringe with the same ID and a second inventory token.
        if (_at < 0) then {_store pushBack _returned;} else {
            private _row = +(_store select _at);
            _row set [2,(_row param [2,0]) + (_returned param [2,0])];
            _row set [4,(_row param [4,0]) + (_returned param [4,0])];
            private _parts = +(_row param [5,[],[[]]]);
            {
                _x params ["_med","_ml"];
                private _ci = _parts findIf {(_x param [0,""]) == _med};
                if (_ci < 0) then {_parts pushBack [_med,_ml];} else {
                    private _part = +(_parts select _ci);
                    _part set [1,(_part select 1)+_ml];
                    _parts set [_ci,_part];
                };
            } forEach (_returned param [5,[],[[]]]);
            _row set [5,_parts];
            if ((_row param [6,""]) == "epiMixB12") then {
                private _ml = (_row select 2)+(_row select 4);
                _row set [3,format ["Push-dose epinephrine 10 mcg/mL (%1 mL = %2 mcg left)",_ml toFixed 1,(_ml*10) toFixed 0]];
            };
            _store set [_at,_row];
        };
    } forEach _drawn;
    [_medic, _store] call ACME_fnc_narcStoreCommit;
    if (_medic isEqualTo ACE_player) then {
        [_medic] call ACME_fnc_skStoreEnsureIds;
        if (!isNull (findDisplay 84000)) then {call ACME_fnc_skRefreshDrawn;};
    };
};
