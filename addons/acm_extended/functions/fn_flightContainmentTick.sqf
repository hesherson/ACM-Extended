/* Bounded owner-local aircraft floor lease; never a ground snap or immunity.
 * One per-frame callback per supported unconscious casualty, none for freefall.
 * Native skeleton/ragdoll presentation remains an in-engine acceptance check. */
params ["_args","_pfh"];
_args params ["_patient","_serial"];
if (isNull _patient) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _record = _patient getVariable ["ACME_flightContainment",[]];
if (count _record != 10 || {(_record select 0) != _serial}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
if (!local _patient || {(_record select 7) != clientOwner}) exitWith {
    [_patient,_serial,true] call ACME_fnc_flightContainmentStop;
};
_record params ["","_air","_feet","_root","_epoch","","_lastRoot","","_lastTime","_lastVelocity"];
private _retire = !alive _patient || {isNull _air} || {!alive _air}
    || {!(_patient getVariable ["ACE_isUnconscious",false])}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
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
    || {((toLowerANSI animationState _patient) find "halofreefall") >= 0}
    || {((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime};
if (_retire) exitWith {[_patient,_serial] call ACME_fnc_flightContainmentStop;};
private _anchor = _air modelToWorldWorld _root;
private _position = getPosWorld _patient;
// The body integrates the exact velocity this worker wrote between frames.
// A delayed/smoothed remote carrier sample can be ahead of that legitimate
// motion, placing the body between the last root and new anchor. Accept only
// the exact owned-velocity prediction within the same tight displacement limit.
// A long stall, clock rollback/nonfinite value, or missing motion record cannot
// grant prediction. Actual floor contact is still validated before any write.
private _predictedDistance = 1e30;
if (_lastTime isEqualType 0 && {finite _lastTime}
    && {CBA_missionTime isEqualType 0} && {finite CBA_missionTime}
    && {_lastVelocity isEqualType []} && {count _lastVelocity == 3}
    && {(_lastVelocity findIf {!(_x isEqualType 0) || {!finite _x}}) < 0}) then {
    private _elapsed = CBA_missionTime - _lastTime;
    if (_elapsed >= 0 && {_elapsed <= 5}) then {
        private _predictedRoot = _lastRoot vectorAdd (_lastVelocity vectorMultiply _elapsed);
        _predictedDistance = _position vectorDistance _predictedRoot;
    };
};
// A different script's teleport/ejection must not be dragged back into the
// cabin. Aircraft translation itself is allowed, including a teleported plane.
if ((((_position vectorDistance _lastRoot) min (_position vectorDistance _anchor)) min _predictedDistance) > 1.5) exitWith {
    [_patient,_serial] call ACME_fnc_flightContainmentStop;
};
// Validate the OWNED floor point, not a ragdoll's temporarily displaced feet.
// An animated open ramp/missing floor/deleted support releases this lease.
private _contact = [_patient,_air modelToWorldWorld _feet,_air,false] call ACME_fnc_flightSupport;
if (_contact isEqualTo []) exitWith {[_patient,_serial] call ACME_fnc_flightContainmentStop;};
_patient setPosWorld _anchor;
private _velocity = velocity _air;
_patient setVelocity _velocity;
_record set [6,_anchor];
_record set [8,CBA_missionTime];
_record set [9,+_velocity];
