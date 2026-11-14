/* Shared monotonic time. Preserve the native mission timestamp origin for ACE
 * medication records and fresh-blood donor facts. Cooler custody uses server time. */
params [["_missionOrigin",false]];
private _now = serverTime;
private _anchor = missionNamespace getVariable ["ACME_clinicalClockAnchor",[]];
if (_anchor isEqualTo []) exitWith {[_now,CBA_missionTime] select _missionOrigin};
_anchor params ["_at","_offset","_rate","_missionOffset"];
_now + ([0,_missionOffset] select _missionOrigin) + _offset + (((_now - _at) max 0) * (_rate - 1))
