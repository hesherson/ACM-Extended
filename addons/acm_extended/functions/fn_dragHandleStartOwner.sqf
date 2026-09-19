// Experimental drag handles are available only in HEMTT dev/launch builds.
if (getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acme_developmentBuild") != 1) exitWith {};
// Patient-owner authoritative drag-handle start.
// The patient remains unattached. Its owner drives a real PhysX ragdoll with addForce impulses.
params [["_patient",objNull,[objNull]],["_medic",objNull,[objNull]]];
if (isNull _patient || {isNull _medic}) exitWith {};
if (!local _patient) exitWith {[_patient,"dragHandleStart",[_patient,_medic]] call ACME_fnc_ownerDispatch;};

private _reject = {
    params ["_reason"];
    ["ACME_dragHandle_startAck",[_medic,_patient,false,0,_reason],_medic] call CBA_fnc_targetEvent;
};

if !(missionNamespace getVariable ["ACME_dragHandle_enabled",true]) exitWith {["Drag handle is disabled."] call _reject;};
if (_medic isEqualTo _patient) exitWith {["You cannot attach a drag handle to yourself."] call _reject;};
if (!alive _patient || {!alive _medic}) exitWith {["Casualty or dragger is not alive."] call _reject;};
if (_medic getVariable ["ACE_isUnconscious",false]) exitWith {["You cannot attach a drag handle while unconscious."] call _reject;};
if !((_patient getVariable ["ACE_isUnconscious",false]) || {lifeState _patient == "INCAPACITATED"}) exitWith {["Casualty must be unconscious."] call _reject;};
if (!(isNull (objectParent _patient)) || {!(isNull (objectParent _medic))}) exitWith {["Cannot attach the drag handle in a vehicle."] call _reject;};
if ((_patient getVariable ["ACME_dragHandle_active",false])) exitWith {["That casualty already has a drag handle attached."] call _reject;};
if (!isNull (_medic getVariable ["ACME_dragHandle_patient",objNull])) exitWith {["You already have a drag handle attached."] call _reject;};
if ((_patient call ace_common_fnc_isBeingDragged) || {_patient call ace_common_fnc_isBeingCarried}) exitWith {["Casualty is already being moved."] call _reject;};
if (_medic getVariable ["ace_dragging_isDragging",false] || {_medic getVariable ["ace_dragging_isCarrying",false]}) exitWith {["Finish the current ACE drag/carry first."] call _reject;};

if (!isNil "ace_common_fnc_canInteractWith"
    && {!([_medic,_patient,[]] call ace_common_fnc_canInteractWith)}) exitWith {
    ["You cannot interact with the casualty right now."] call _reject;
};

private _interactionOwner = _patient getVariable ["ace_common_owner",objNull];
if (!isNull _interactionOwner && {_interactionOwner isNotEqualTo _medic}) exitWith {
    ["Another provider currently owns the casualty interaction."] call _reject;
};

private _attachDist = missionNamespace getVariable ["ACME_dragHandle_attachDistance",2.3];
if ((_medic distance _patient) > (_attachDist + 0.35)) exitWith {["Move closer to the casualty."] call _reject;};

if (!(isNull (attachedTo _patient)) && {!(_patient getVariable ["ACME_headElevated",false])}) exitWith {
    ["Another system currently owns the casualty position."] call _reject;
};

private _lock = _patient getVariable ["ACME_patientAnimLock",[]];
if ((count _lock) >= 5 && {(_lock param [4,-1]) > CBA_missionTime}) exitWith {["A procedure currently owns the casualty position."] call _reject;};

// Use the same head-elevation transport handoff as ACE drag/carry.
if (_patient getVariable ["ACME_headElevated",false]) then {
    ["ACME_headElev_transportDown",[_patient]] call CBA_fnc_localEvent;
};

// Preserve ACE's person-drag flags, then hide its rigid attachTo drag/carry actions while this handle owns movement.
private _oldCanDrag = _patient getVariable ["ace_dragging_canDrag",true];
private _oldCanCarry = _patient getVariable ["ace_dragging_canCarry",true];
_patient setVariable ["ACME_dragHandle_oldAceFlags",[_oldCanDrag,_oldCanCarry],true];
_patient setVariable ["ace_dragging_canDrag",false,true];
_patient setVariable ["ace_dragging_canCarry",false,true];

private _weight = [_patient] call ACME_fnc_dragHandleWeight;
private _serial = (missionNamespace getVariable ["ACME_dragHandle_sessionSerial",0]) + 1;
missionNamespace setVariable ["ACME_dragHandle_sessionSerial",_serial];
private _session = format ["dh:%1:%2:%3",owner _patient,floor (CBA_missionTime * 1000),_serial];

_patient setVariable ["ACME_dragHandle_active",true,true];
_patient setVariable ["ACME_dragHandle_dragger",_medic,true];
_patient setVariable ["ACME_dragHandle_weight",_weight,true];
_patient setVariable ["ACME_dragHandle_session",_session,true];
_patient setVariable ["ACME_dragHandle_tension",0];
_patient setVariable ["ACME_dragHandle_startedAt",CBA_missionTime];
_patient setVariable ["ACME_dragHandle_overstretchSince",-1];

// A seizure remains physiologically active, but the spasm gesture yields to the live ragdoll while it is being dragged.
// fn_seizureMotion also checks this flag so the physiology tick cannot immediately restart the gesture.
if (!isNil "ACME_fnc_seizureMotion" && {(_patient getVariable ["ACME_lido_seizureState",""]) == "active"}) then {
    [_patient,false] call ACME_fnc_seizureMotion;
};

private _ropeObjects = [_patient,_medic,true] call ACME_fnc_dragHandleRope;
if (_ropeObjects isEqualTo []) exitWith {
    [_patient,_medic,"rope_failed"] call ACME_fnc_dragHandleStopOwner;
    ["Could not attach the drag rope."] call _reject;
};

// Wake a fresh ragdoll from ACE's normally locked unconscious pose.
[_patient] call ACME_fnc_forceRagdoll;

private _oldPFH = _patient getVariable ["ACME_dragHandle_forcePFH",-1];
if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

private _args = [_patient,_medic,_weight,CBA_missionTime,_ropeObjects];
private _pfh = [{_this call ACME_fnc_dragHandleOwnerTick;},0,_args] call CBA_fnc_addPerFrameHandler;
_patient setVariable ["ACME_dragHandle_forcePFH",_pfh];

["ACME_dragHandle_startAck",[_medic,_patient,true,_weight,"",_session],_medic] call CBA_fnc_targetEvent;
