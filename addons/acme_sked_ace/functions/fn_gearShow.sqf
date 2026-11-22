/*
 * Where the casualty is local: dress a casualty who comes off a litter in everything fn_gearHide.sqf took off.
 * The kept loadout is put back whole. Two things can differ from the moment they were undressed:
 *   - an HPMK-I worn as a vest (put on, or changed, while they were strapped) stays on; the vest it displaces,
 *     helmet and night vision are remembered and come back when the shell comes off (ACME_fnc_hpmkDress);
 *   - what was given to them while they were undressed and is not in the kept loadout is laid beside them.
 * If the loadout does not go back on (a casualty who has died meanwhile), all of it is laid beside them.
 * Nothing is lost in any of these cases. The copies are cleared only after that.
 * Arguments: 0: casualty, 1: the server's copy of the loadout (default: none).
 */
params ["_patient", ["_copy", []]];
if (!local _patient) exitWith {};
private _kept = _patient getVariable ["acme_sked_gear", []];
if (_kept isEqualTo []) then {_kept = _copy;};
if (_kept isEqualTo []) exitWith {};
_kept params ["_saved", ["_extended", []]];
private _hpmk = ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"];
private _now = getUnitLoadout _patient;
private _beside = [];
private _done = false;
if (alive _patient) then {
    private _back = +_saved;
    private _nowVest = _now select 4;
    private _savedVest = _saved select 4;
    if (_nowVest isNotEqualTo [] && {(_nowVest select 0) in _hpmk}) then {
        // He is wrapped in the HPMK: the shell stays on. It takes the place of his own vest as it does off a
        // litter (ACME_fnc_hpmkDress): what was in the vest goes into the shell's pockets, and vest, helmet and
        // night vision are remembered and put back when the shell comes off.
        _nowVest = +_nowVest;
        private _stowed = +(_patient getVariable ["ACME_hpmk_stowed", ["", "", ""]]);
        if (count _stowed < 3) then {_stowed = ["", "", ""];};
        if (_savedVest isNotEqualTo [] && {!((_savedVest select 0) in _hpmk)}) then {
            if ((_stowed select 0) == "") then {
                _stowed set [0, _savedVest select 0];
                (_nowVest select 1) append (_savedVest select 1);
            } else {
                _beside pushBack [[], [], [], [], _savedVest, [], "", "", [], ["", "", "", "", "", ""]];
            };
        };
        if ((_back select 6) != "") then {
            if ((_stowed select 1) == "") then {_stowed set [1, _back select 6];};
            _back set [6, ""];
        };
        private _nvg = (_back select 9) param [5, ""];
        if (_nvg != "") then {
            if ((_stowed select 2) == "") then {_stowed set [2, _nvg];};
            (_back select 9) set [5, ""];
        };
        _patient setVariable ["ACME_hpmk_stowed", _stowed, true];
        _back set [4, _nowVest];
    } else {
        if (_savedVest isNotEqualTo [] && {(_savedVest select 0) in _hpmk}) then {_back set [4, []];};
    };
    // anything they hold now that is not an HPMK: it was given to them while they were undressed
    private _extra = +_now;
    if ((_extra select 4) isNotEqualTo [] && {((_extra select 4) select 0) in _hpmk}) then {_extra set [4, []];};
    if (_extra isNotEqualTo [[], [], [], [], [], [], "", "", [], ["", "", "", "", "", ""]]) then {_beside pushBack _extra;};
    if (_extended isEqualType [] && {count _extended == 2} && {!isNil "CBA_fnc_setLoadout"}) then {
        [_patient, [_back, _extended select 1], false] call CBA_fnc_setLoadout;
    } else {
        _patient setUnitLoadout [_back, false];
    };
    private _after = getUnitLoadout _patient;
    _done = ((_after select 3) param [0, ""]) == ((_back select 3) param [0, ""])
        && {((_after select 5) param [0, ""]) == ((_back select 5) param [0, ""])}
        && {((_after select 0) param [0, ""]) == ((_back select 0) param [0, ""])}
        && {(_after select 6) == (_back select 6)};
    if (!_done) then {
        // It did not take: put on them what the plain command can, and lay the kept loadout beside them as well
        // only if even that fails.
        _patient setUnitLoadout [_back, false];
        _after = getUnitLoadout _patient;
        _done = ((_after select 3) param [0, ""]) == ((_back select 3) param [0, ""])
            && {((_after select 5) param [0, ""]) == ((_back select 5) param [0, ""])};
    };
};
if (!_done) then {_beside pushBack _saved;};
{[_patient, _x] call acme_sked_fnc_gearDrop;} forEach _beside;
["gear given back", objNull, _patient, [_done, count _beside]] call acme_sked_fnc_traceTransport;
_patient setVariable ["acme_sked_gear", nil, true];
["acme_sked_gearGone", [_patient]] call CBA_fnc_serverEvent;
