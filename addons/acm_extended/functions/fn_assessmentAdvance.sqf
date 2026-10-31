/* Exact source sample then immediate graph interpolation. Caller owns the current epoch and phase. */
params ["_medic", "_pose", "_record", "_duration"];
if (!local _medic || {(_record select 2) != 1} || {_pose param [20, false]}
    || {(_pose select 0) != (_record select 0)}
    || {!((_medic getVariable ["ACME_assessment", []]) isEqualTo _record)}
    || {!((_medic getVariable ["ACME_treatmentPoseState", []]) isEqualTo _pose)}) exitWith {};
// At normal speed the initial inspection uses 1.75 native seconds. No persistent freeze event is sent:
// a reordered hold packet could otherwise freeze a peer after the finite medic4 continuation has started.
_medic switchMove ["AinvPknlMstpSnonWnonDr_medic5", 1.75 / _duration, 1, false];
_medic setAnimSpeedCoef 0;
private _next = "AinvPknlMstpSnonWnonDr_medic4";
_pose set [2, _next];
_pose set [3, 1];
_pose set [4, CBA_missionTime];
_pose set [11, -1];
_record set [2, 2];
_record set [7, -1];
_record set [8, -1];
_record set [9, CBA_missionTime];
_medic setAnimSpeedCoef 1;
[_medic, _next, 1] call ACME_fnc_doAnim;
