/* B395: line tension. "any kind of line, whether it's IV or AED or anything else, adds resistance when you're nearing
 * the end of the range before it finally snaps and disconnects" (2026-11-23).
 * Every machine with a player checks, five times a second, the lines that player is pulling: lines from the player
 * (a bag held up, an O2 mask's tubing from the tank they carry) and lines from whatever the player is moving
 * (a casualty dragged or carried, on a litter too, an IV pole or a monitor/AED being moved). Over the last 30 % of a
 * line's reach the player is slowed, more and more (down to 30 % speed, walking only past half of that stretch), and
 * told the line is pulling tight; at its end the line's own system disconnects it (the reaches and the disconnects
 * are theirs: Hang Bag and IV stands ACME_hang_leash 3 m, monitor and AED leads 6 m, O2 mask ACME_nrb_maxDistance
 * 6 m) and the player hears it go. The speed goes through acme_sked_fnc_paceApply as its third share
 * (acme_line_coef), so it multiplies with the drag and litter paces instead of fighting them.
 * _this: "register" (fn_postInit) or "tick". */
params [["_mode", "tick"]];
if (_mode == "register") exitWith {
    if (!hasInterface || {!isNil "ACME_lineTension_pfh"}) exitWith {};
    ACME_lineTension_tight = createHashMap;
    ACME_lineTension_pfh = [{"tick" call ACME_fnc_lineTension}, 0.2] call CBA_fnc_addPerFrameHandler;
};
private _p = call ACME_fnc_controlledProvider;
if (isNull _p || {!alive _p}) exitWith {};
private _leash = missionNamespace getVariable ["ACME_hang_leash", 3];
private _nrbMax = missionNamespace getVariable ["ACME_nrb_maxDistance", 6];
private _devMax = 6;

// what the player moves: themself, what is attached to them (ACE drag/carry, a litter), and what rides on that
private _movers = [_p];
{
    _movers pushBackUnique _x;
    {_movers pushBackUnique _x;} forEach attachedObjects _x;
} forEach attachedObjects _p;
{
    private _towed = _p getVariable [_x, objNull];
    if (_towed isEqualType objNull && {!isNull _towed}) then {_movers pushBackUnique _towed; {_movers pushBackUnique _x;} forEach attachedObjects _towed;};
} forEach ["acme_drag_target", "acme_carry_litter", "acme_sked_bearing"];

// [mover, other end, reach, kind]
private _lines = [];
private _add = {
    params ["_a", "_b", "_max", "_kind"];
    if (!isNull _b && {!(_b in _movers)} && {_max > 0}) then {_lines pushBack [_a, _b, _max, _kind];};
};
{
    private _m = _x;
    switch (true) do {
        case (_m isEqualTo _p): {
            if (_p getVariable ["ACME_hang_Active", false]) then {[_p, _p getVariable ["ACME_hang_Patient", objNull], _leash, "held IV line"] call _add;};
            {
                if ((_x getVariable ["ACME_nrb_medic", objNull]) isEqualTo _p && {_x getVariable ["ACME_nrb_on", false]}) then {[_p, _x, _nrbMax, "oxygen tubing"] call _add;};
            } forEach (_p nearEntities ["CAManBase", _nrbMax + 2]);
        };
        case (_m isKindOf "CAManBase"): {
            {[_m, _x, _leash, "IV line"] call _add;} forEach ((_m nearObjects ["Land_IntravenStand_01_base_F", _leash + 2]) select {_m in (_x getVariable ["ACME_ivStand_slots", []])});
            private _holder = _m getVariable ["ACME_hang_Medic", objNull];
            if (!isNull _holder && {_holder getVariable ["ACME_hang_Active", false]}) then {[_m, _holder, _leash, "IV line"] call _add;};
            {
                if ((_x getVariable ["acme_tempus_pat", objNull]) isEqualTo _m) then {[_m, _x, _devMax, "monitor leads"] call _add;};
                if ((_x getVariable ["acme_tempusls_pat", objNull]) isEqualTo _m) then {[_m, _x, _devMax, "AED pads"] call _add;};
            } forEach (_m nearObjects ["Items_base_F", _devMax + 2]);
            private _nrbMedic = _m getVariable ["ACME_nrb_medic", objNull];
            if (!isNull _nrbMedic && {_m getVariable ["ACME_nrb_on", false]}) then {[_m, _nrbMedic, _nrbMax, "oxygen tubing"] call _add;};
        };
        case (_m isKindOf "Land_IntravenStand_01_base_F"): {
            {if (!isNull _x) then {[_m, _x, _leash, "IV line"] call _add;};} forEach (_m getVariable ["ACME_ivStand_slots", []]);
        };
        default {
            [_m, _m getVariable ["acme_tempus_pat", objNull], _devMax, "monitor leads"] call _add;
            [_m, _m getVariable ["acme_tempusls_pat", objNull], _devMax, "AED pads"] call _add;
        };
    };
} forEach _movers;

// how tight: 0 up to 70 % of the reach, 1 at its end
private _start = 0.7;
private _worst = 0;
private _worstKind = "";
private _tight = createHashMap;
{
    _x params ["_a", "_b", "_max", "_kind"];
    private _t = (((_a distance _b) - _start * _max) / ((1 - _start) * _max)) max 0 min 1;
    if (_t > _worst) then {_worst = _t; _worstKind = _kind;};
    if (_t > 0.8) then {_tight set [format ["%1|%2|%3", hashValue _a, hashValue _b, _kind], [_a, _b, _kind]];};
} forEach _lines;

// a line that was at its end a moment ago and whose connection has ended since has snapped (not one that went slack
// or that the player let go of: its connection is still there)
private _connected = {
    params ["_a", "_b", "_kind"];
    private _pair = [_a, _b];
    switch (_kind) do {
        case "IV line": {
            (_pair findIf {(_x isKindOf "Land_IntravenStand_01_base_F") && {((_pair - [_x]) select 0) in (_x getVariable ["ACME_ivStand_slots", []])}}) >= 0
            || {(_pair findIf {(_x getVariable ["ACME_hang_Active", false]) && {((_pair - [_x]) select 0) isEqualTo (_x getVariable ["ACME_hang_Patient", objNull])}}) >= 0}
        };
        case "held IV line": {(_pair findIf {(_x getVariable ["ACME_hang_Active", false]) && {((_pair - [_x]) select 0) isEqualTo (_x getVariable ["ACME_hang_Patient", objNull])}}) >= 0};
        case "oxygen tubing": {(_pair findIf {(_x getVariable ["ACME_nrb_on", false]) && {((_pair - [_x]) select 0) isEqualTo (_x getVariable ["ACME_nrb_medic", objNull])}}) >= 0};
        case "monitor leads": {(_pair findIf {((_pair - [_x]) select 0) isEqualTo (_x getVariable ["acme_tempus_pat", objNull])}) >= 0};
        case "AED pads": {(_pair findIf {((_pair - [_x]) select 0) isEqualTo (_x getVariable ["acme_tempusls_pat", objNull])}) >= 0};
        default {true};
    };
};
{
    if (!(_x in _tight) && {!(_y call _connected)}) then {
        // (a held bag says so itself: "Out of line range. Bag lowered.")
        if ((_y select 2) != "held IV line") then {[format ["The %1 pulled free.", _y select 2], 2] call ace_common_fnc_displayTextStructured;};
        // the game's sling-load rope snapping, softer and higher
        playSound3D ["a3\sounds_f\air\sfx\SL_rope_break.wss", _p, false, getPosASL _p, 0.5, 1.6, 20];
    };
} forEach ACME_lineTension_tight;
ACME_lineTension_tight = _tight;

// the pull on the player
private _coef = 1 - 0.7 * (_worst ^ 1.5);
private _old = _p getVariable ["acme_line_coef", 1];
if (abs (_coef - _old) > 0.02 || {_coef == 1 && {_old != 1}}) then {
    _p setVariable ["acme_line_coef", [_coef, nil] select (_coef >= 0.999)];
    if (!isNil "acme_sked_fnc_paceApply") then {[_p] call acme_sked_fnc_paceApply;} else {_p setAnimSpeedCoef _coef;};
};
private _walk = _worst > 0.5;
if (_walk isNotEqualTo (_p getVariable ["ACME_lineTension_walk", false])) then {
    _p setVariable ["ACME_lineTension_walk", _walk];
    [_p, "forceWalk", "ACME_lineTension", _walk] call ace_common_fnc_statusEffect_set;
};
if (_worst > 0.3 && {CBA_missionTime > (_p getVariable ["ACME_lineTension_saidAt", -10]) + 4}) then {
    _p setVariable ["ACME_lineTension_saidAt", CBA_missionTime];
    [format ["The %1 is pulling tight.", _worstKind regexReplace ["held ", ""]], 1.5] call ace_common_fnc_displayTextStructured;
};
