/* Recover durable supply escrow after dialog close or provider-locality handoff.
 * Settled rows remain as terminal evidence; no timeout invents a supply refund. */
params [["_medic", objNull, [objNull]]];
if (isNull _medic || {!local _medic}) exitWith {false};
private _escrow = _medic getVariable ["ACME_lineWarmerEscrow", createHashMap];
private _pending = (values _escrow) select {!(_x param [1, true])};
if (_pending isEqualTo []) exitWith {true};
{private _request = _x select 0; [_request select 0, "lineWarmer", _request] call ACME_fnc_ownerDispatch;} forEach _pending;
private _recoverHandlers = missionNamespace getVariable ["ACME_lineWarmerRecoverHandlers", createHashMap];
private _key = str _medic;
if (_key in _recoverHandlers) exitWith {true};
private _handle = [{
    params ["_args", "_handle"];
    _args params ["_medic", "_key"];
    private _escrow = _medic getVariable ["ACME_lineWarmerEscrow", createHashMap];
    private _pending = (values _escrow) select {!(_x param [1, true])};
    if (isNull _medic || {!local _medic} || {_pending isEqualTo []}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        (missionNamespace getVariable ["ACME_lineWarmerRecoverHandlers", createHashMap]) deleteAt _key;
    };
    {private _request = _x select 0; [_request select 0, "lineWarmer", _request] call ACME_fnc_ownerDispatch;} forEach _pending;
}, 0.75, [_medic, _key]] call CBA_fnc_addPerFrameHandler;
_recoverHandlers set [_key, _handle];
missionNamespace setVariable ["ACME_lineWarmerRecoverHandlers", _recoverHandlers];
true
