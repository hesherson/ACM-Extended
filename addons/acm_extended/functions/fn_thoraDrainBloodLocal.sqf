#include "\x\ACM\addons\main\script_macros.hpp"
/* B212: remove retained pleural blood, never its hemorrhage source.
 * ACM owns ONE casualty-wide fluid reservoir, not one reservoir per lung.
 * Returns drained liters, or -1 for a stale/duplicate/invalid transaction.
 * Finger widening/sweeping removes the complete pool that exists at this instant.
 * A seal lift drains a pressure-scaled fraction: max(PTX pressure, fluid / native
 * tension-hemothorax threshold), clamped to 0..1. This is gameplay scaling; it does
 * not continuously drain a finger tract or turn a seal into a chest tube.
 */
params ["_patient", "_medic", "_mode", "_epoch", ["_request", []], ["_show", true]];
if (isNull _patient || {!local _patient} || {isNull _medic}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_mode in ["finger", "seal"])}) exitWith {-1};

// Per-origin high-water marks survive ownership transfer. Age validation prevents
// ancient messages from becoming valid after receipt eviction; the bounded table
// supports 256 simultaneous request origins in the same clinical episode.
if !(_request isEqualTo []) then {
    if !(_request isEqualType []) exitWith {_mode = "";};
    if (count _request != 3 || {(_request findIf {!(_x isEqualType 0) || {!finite _x}}) >= 0}) exitWith {_mode = "";};
    _request params ["_origin", "_sequence", "_issued"];
    if (_origin < 0 || {_origin != floor _origin} || {_sequence < 1}
        || {_sequence != floor _sequence} || {serverTime - _issued > 15}
        || {_issued - serverTime > 2}) exitWith {_mode = "";};
    private _receipts = _patient getVariable ["ACME_pleuralDrainReceipts", [-1, []]];
    private _rows = if ((_receipts param [0, -1]) == _epoch) then {+(_receipts param [1, []])} else {[]};
    _rows = _rows select {serverTime - (_x select 2) <= 15};
    private _index = _rows findIf {(_x select 0) == _origin};
    if (_index >= 0 && {_sequence <= ((_rows select _index) select 1)}) exitWith {_mode = "";};
    if (_index < 0 && {count _rows >= 256}) exitWith {_mode = "";};
    if (_index < 0) then {_rows pushBack [_origin, _sequence, _issued];}
    else {_rows set [_index, [_origin, _sequence, _issued]];};
    _patient setVariable ["ACME_pleuralDrainReceipts", [_epoch, _rows], true];
};
if (_mode == "") exitWith {-1};

private _fluid = _patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
if !(_fluid isEqualType 0 && {finite _fluid}) exitWith {-1};
_fluid = _fluid max 0;
private _fraction = 1;
if (_mode == "seal") then {
    private _state = _patient getVariable ["ACME_ptx_state", []];
    private _pressure = if (_state isEqualType []) then {_state param [4, 0]} else {0};
    if !(_pressure isEqualType 0 && {finite _pressure}) then {_pressure = 0;};
    if (_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]) then {_pressure = 1;};
    _fraction = (_pressure max (_fluid / ACM_TENSIONHEMOTHORAX_THRESHOLD)) max 0 min 1;
};
private _drained = (_fluid * _fraction) min _fluid;
private _remaining = (_fluid - _drained) max 0;
if (_drained > 0) then {
    [_patient, [["hemothoraxFluid", _remaining]], true] call ACM_breathing_fnc_setRuntimeState;
    // Do not double-count a finger/seal spill as measured chest-tube output.
    // Keep any opposite-side tube's inflow observer synchronized with the debit.
    [_patient, "fluidSeen", _remaining, false] call ACME_fnc_thoraOutputStateCommit;
};
if (_show) then {
    private _label = if (_mode == "finger") then {"Finger thoracostomy"} else {"Chest seal released"};
    ["ace_common_displayTextStructured", [["%1<br/>Blood drained: %2 mL", _label, (round (_drained * 10000)) / 10],
        3, _medic, 13], _medic] call CBA_fnc_targetEvent;
};
_drained
