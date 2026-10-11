/* Reconstruct provider requests from replicated physical custody on Local/reopen.
   A lost local pending map cannot strand a reserved bag or fabricate a stock refund. */
params ["_medic",["_dispatch",true]];
if (isNull _medic || {!local _medic}) exitWith {};
private _escrow = _medic getVariable ["ACME_piggybackEscrow",createHashMap];
private _requests = missionNamespace getVariable ["ACME_piggybackRequests",createHashMap];
private _retry = [];
{
    private _held = _y;
    private _args = _held param [6,[]];
    if (count _args != 12 || {!((_args select 0) isEqualTo _medic)}) then {continue;};
    private _id = _held select 0;
    private _known = _requests getOrDefault [_id,[]];
    if (_known isEqualTo [] || {_known param [2,false]} || {CBA_missionTime - (_known param [1,0]) > 120}) then {
        _requests set [_id,[_args,CBA_missionTime,false]];
        _retry pushBack _id;
    };
} forEach _escrow;
missionNamespace setVariable ["ACME_piggybackRequests",_requests];
if (_dispatch) then {{[_x] call ACME_fnc_piggybackRetry;} forEach _retry;};
