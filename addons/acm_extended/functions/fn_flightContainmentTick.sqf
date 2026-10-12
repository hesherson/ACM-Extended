/* Bounded owner-local aircraft floor lease; never a ground snap or immunity.
 * One per-frame callback per supported unconscious casualty, none for freefall.
 * Native skeleton/ragdoll presentation remains an in-engine acceptance check. */
params ["_args","_pfh"];
_args params ["_patient","_serial"];
if (isNull _patient) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _record = _patient getVariable ["ACME_flightContainment",[]];
if (count _record != 8 || {(_record select 0) != _serial}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
if (!local _patient || {(_record select 7) != clientOwner}) exitWith {
    [_patient,_serial,true] call ACME_fnc_flightContainmentStop;
};
_record params ["","_air","_feet","_root","_epoch","","_lastRoot"];
private _retire = !alive _patient || {isNull _air} || {!alive _air}
    || {!(_patient getVariable ["ACE_isUnconscious",false])}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!isNull objectParent _patient} || {!isNull attachedTo _patient}
    || {_patient getVariable ["ace_dragging_isDragged",false]}
    || {_patient getVariable ["ace_dragging_isCarried",false]}
    || {((toLowerANSI animationState _patient) find "halofreefall") >= 0}
    || {((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime};
if (_retire) exitWith {[_patient,_serial] call ACME_fnc_flightContainmentStop;};
private _anchor = _air modelToWorldWorld _root;
private _position = getPosWorld _patient;
// A different script's teleport/ejection must not be dragged back into the
// cabin. Aircraft translation itself is allowed, including a teleported plane.
if (((_position vectorDistance _lastRoot) min (_position vectorDistance _anchor)) > 1.5) exitWith {
    [_patient,_serial] call ACME_fnc_flightContainmentStop;
};
// Validate the OWNED floor point, not a ragdoll's temporarily displaced feet.
// An animated open ramp/missing floor/deleted support releases this lease.
private _contact = [_patient,_air modelToWorldWorld _feet,_air,false] call ACME_fnc_flightSupport;
if (_contact isEqualTo []) exitWith {[_patient,_serial] call ACME_fnc_flightContainmentStop;};
_patient setPosWorld _anchor;
_patient setVelocity velocity _air;
_record set [6,_anchor];
