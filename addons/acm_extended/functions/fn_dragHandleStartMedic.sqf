// Experimental drag handles are available only in HEMTT dev/launch builds.
if (getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acme_developmentBuild") != 1) exitWith {};
// Local dragger movement/load controller after the patient owner accepts the transaction.
params [["_medic",objNull,[objNull]],["_patient",objNull,[objNull]],["_weight",350,[0]],["_session","",[""]]];
if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {};

_medic setVariable ["ACME_dragHandle_pending",false];
// A stop can legitimately race the start acknowledgement, for example if the line overstretches immediately.
// Never install provider restrictions for a transaction the patient owner has already torn down.
if (_session != "" && {(_medic getVariable ["ACME_dragHandle_lastStoppedSession",""]) == _session}) exitWith {};
if (!(_patient getVariable ["ACME_dragHandle_active",false])
    || {(_patient getVariable ["ACME_dragHandle_dragger",objNull]) isNotEqualTo _medic}
    || {_session != "" && {(_patient getVariable ["ACME_dragHandle_session",""]) != _session}}) exitWith {};

_medic setVariable ["ACME_dragHandle_patient",_patient,true];
_medic setVariable ["ACME_dragHandle_session",_session];
_medic setVariable ["ACME_dragHandle_weight",_weight];
_medic setVariable ["ACME_dragHandle_tension",0];

private _savedCoef = getAnimSpeedCoef _medic;
if !(_savedCoef isEqualType 0 && {finite _savedCoef} && {_savedCoef >= 0}) then {_savedCoef = 1;};
_medic setVariable ["ACME_dragHandle_savedAnimCoef",_savedCoef];
_medic setVariable ["ACME_dragHandle_lastAnimCoef",-1];

// Do not let ACE advanced fatigue overwrite our locomotion cap while the harness owns movement speed.
if (!isNil "ace_advanced_fatigue_setAnimExclusions") then {
    ace_advanced_fatigue_setAnimExclusions pushBackUnique "ACME_dragHandle";
};

// Sprint is independently blocked, so even another addon raising anim speed cannot turn this into a full sprint.
if (!isNil "ace_common_fnc_statusEffect_set") then {
    [_medic,"blockSprint","ACME_dragHandle",true] call ace_common_fnc_statusEffect_set;
} else {
    _medic allowSprint false;
};

private _oldPFH = _medic getVariable ["ACME_dragHandle_medicPFH",-1];
if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

private _pfh = [{
    params ["_args","_handle"];
    _args params ["_medic","_patient","_weight"];

    if (isNull _medic || {!local _medic}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    if (isNull _patient) exitWith {
        [_medic,objNull,"lost"] call ACME_fnc_dragHandleStopMedic;
    };
    if (!(_patient getVariable ["ACME_dragHandle_active",false])
        || {(_patient getVariable ["ACME_dragHandle_dragger",objNull]) isNotEqualTo _medic}) exitWith {
        [_medic,_patient,"lost"] call ACME_fnc_dragHandleStopMedic;
    };

    if (!alive _medic || {_medic getVariable ["ACE_isUnconscious",false]}
        || {!(isNull (objectParent _medic))}
        || {_medic getVariable ["ace_dragging_isDragging",false]}
        || {_medic getVariable ["ace_dragging_isCarrying",false]}
        || {_medic isNotEqualTo ACE_player}) exitWith {
        [_medic,_patient,"dragger_invalid"] call ACME_fnc_dragHandleStop;
    };

    private _handleModel = _patient selectionPosition "Spine3";
    if !(_handleModel isEqualType [] && {count _handleModel >= 3} && {vectorMagnitude _handleModel > 0.05}) then {_handleModel=[0,0,0.78];};
    private _pp = _patient modelToWorld _handleModel;
    private _anchor = _medic modelToWorld [0,-0.30,0.55];
    private _dist = _pp vectorDistance _anchor;
    private _slack = missionNamespace getVariable ["ACME_dragHandle_slackLength",1.0];
    private _release = missionNamespace getVariable ["ACME_dragHandle_releaseDistance",2.65];
    private _tension = linearConversion [_slack,_release,_dist,0,1,true];
    _medic setVariable ["ACME_dragHandle_tension",_tension];

    // Light casualties top out at a slow jog. Heavy casualties and a taut/snagged line progressively slow the
    // medic toward a fast walk, making tether tension something the player can feel through locomotion.
    private _lightCoef = missionNamespace getVariable ["ACME_dragHandle_lightAnimCoef",0.62];
    private _heavyCoef = missionNamespace getVariable ["ACME_dragHandle_heavyAnimCoef",0.48];
    private _weightCoef = linearConversion [350,950,_weight,_lightCoef,_heavyCoef,true];
    private _tensionCoef = linearConversion [0,1,_tension,1,0.72,true];
    private _saved = _medic getVariable ["ACME_dragHandle_savedAnimCoef",1];
    private _desired = ((_saved * _weightCoef * _tensionCoef) min _lightCoef) max 0.30;
// Dragging is a cap, never a speed boost. A provider already slowed below our normal floor by another
// authoritative system keeps that lower coefficient.
_desired = _desired min _saved;

    if (abs ((getAnimSpeedCoef _medic) - _desired) > 0.012) then {
        _medic setAnimSpeedCoef _desired;
    };
    _medic setVariable ["ACME_dragHandle_lastAnimCoef",_desired];
},0.05,[_medic,_patient,_weight]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_dragHandle_medicPFH",_pfh];

["Drag handle attached. Sprint disabled; casualty weight and tether tension limit your pace.",2.2,_medic,12] call ace_common_fnc_displayTextStructured;
