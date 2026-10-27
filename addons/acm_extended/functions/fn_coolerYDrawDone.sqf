/* Complete exactly the pending Y-set draw; source delivery itself is durable. */
params ["_ok","_args"];
_args params ["_serial","_context"];
private _pending=missionNamespace getVariable ["ACME_yCoolerDrawPending",[]];
if (_pending isNotEqualTo [_serial,_context]) exitWith {};
missionNamespace setVariable ["ACME_yCoolerDrawPending",[]];
if (!_ok || {isNull(findDisplay 86000)} || {uiNamespace getVariable ["ACME_preparedListMode",false]}
    || {!((missionNamespace getVariable ["ACME_piggybackPending",[]]) isEqualTo [])}) exitWith {};
private _owner=_context select 0;
if (isNull _owner || {_owner isNotEqualTo ACE_player} || {!local _owner} || {!alive _owner}) exitWith {};
// The production Y handler revalidates every saved patient, access, kit and
// component field before scheduling the existing physical build transaction.
[_context] call ACME_fnc_transfusionYTubing;
