/* Capture supported on-foot contact BEFORE the native unconscious/ragdoll edge.
 * ACE's medical state and native incapacitated state remain authoritative.
 * The owner alone holds the model root relative to the confirmed moving floor.
 * This does not establish native ragdoll-skeleton containment on every mod model. */
params [["_patient",objNull,[objNull]], ["_resume",false,[false]]];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {false};
if (!(_patient getVariable ["ACE_isUnconscious",false])
    || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
    || {(_patient getVariable ["ace_dragging_isDragged",false]) isEqualTo true}
    || {(_patient getVariable ["ace_dragging_isCarried",false]) isEqualTo true}
    || {!isNil "ace_common_fnc_isBeingDragged" && {
        private _dragged = _patient call ace_common_fnc_isBeingDragged;
        !isNil "_dragged" && {_dragged isEqualTo true}
    }}
    || {!isNil "ace_common_fnc_isBeingCarried" && {
        private _carried = _patient call ace_common_fnc_isBeingCarried;
        !isNil "_carried" && {_carried isEqualTo true}
    }}
    || {((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}) exitWith {false};
private _current = _patient getVariable ["ACME_flightContainment",[]];
if !(_current isEqualTo []) exitWith {true};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _support = [];
if (_resume) then {
    private _context = _patient getVariable ["ACME_flightContainmentContext",[]];
    if (_context isEqualType [] && {count _context == 5}
        && {(_context select 0) isEqualType 0} && {(_context select 1) isEqualType objNull}
        && {(_context select 4) isEqualType 0} && {(_context select 4) == _epoch}
        && {((_context select [2,2]) findIf {!(_x isEqualType [])
            || {count _x != 3} || {(_x findIf {!(_x isEqualType 0) || {!finite _x}}) >= 0}}) < 0}) then {
        _context params ["_oldSerial","_air","_feet","_root"];
        if (!isNull _air && {alive _air}) then {
            private _anchor = _air modelToWorldWorld _root;
            if ((getPosWorld _patient) vectorDistance _anchor <= 1.5) then {
                private _contact = [_patient,_air modelToWorldWorld _feet,_air,false] call ACME_fnc_flightSupport;
                if !(_contact isEqualTo []) then {_support = [_air,_feet,_root];};
            };
        };
    };
} else {_support = [_patient] call ACME_fnc_flightSupport;};
if (_support isEqualTo []) exitWith {
    _patient setVariable ["ACME_flightContainmentContext",[],true];
    false
};
private _serial = (_patient getVariable ["ACME_flightContainmentSerial",0]) + 1;
_patient setVariable ["ACME_flightContainmentSerial",_serial,true];
_support params ["_air","_feet","_root"];
_patient setVariable ["ACME_flightContainmentContext",[_serial,_air,_feet,_root,_epoch],true];
// Motion prediction is armed only after this worker actually sets root/velocity.
private _record = [_serial,_air,_feet,_root,_epoch,-1,getPosWorld _patient,clientOwner,CBA_missionTime,[]];
_patient setVariable ["ACME_flightContainment",_record,false];
private _pfh = [{_this call ACME_fnc_flightContainmentTick;},0,[_patient,_serial]] call CBA_fnc_addPerFrameHandler;
_record set [5,_pfh];
true
