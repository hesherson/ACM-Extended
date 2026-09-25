// Temporary plate-carrier removal for actions that need a genuinely unobstructed chest while a backpack is worn.
// This is deliberately class-exact. CPR and every explicit BVM treatment variant now share the same carrier custody
// so middle-mouse CPR <-> BVM handoffs cannot re-dress the casualty between maneuvers.
private _maneuverClasses = ["cpr", "usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"];
private _classes = ["usestethoscope", "checkbreathing", "acme_inspectchest"] + _maneuverClasses;
missionNamespace setVariable ["ACME_chestAccess_classes", _classes];
missionNamespace setVariable ["ACME_chestAccess_maneuverClasses", _maneuverClasses];

// The clinical timer owns Check Breathing's frozen provider episode. No wall-clock pose exit may end it early.
{
    [_x, {
        params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
        if (isNull _medic || {!local _medic} || {(toLowerANSI _classname) != "checkbreathing"}) exitWith {};
        private _record = _medic getVariable ["ACME_checkBreathingPose", []];
        if ((_record param [0, objNull]) isNotEqualTo _patient) exitWith {};
        _medic setVariable ["ACME_checkBreathingPose", [], false];
        private _entry = _medic getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [0, objNull]) isEqualTo _patient
            && {(_entry param [1, -1]) == (_record param [1, -2])}) then {
            [_medic, _patient, "stop", false, _entry param [2, ""]] call ACME_fnc_chestAccessVestProvider;
        };
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];

["ace_treatmentStarted", {
    params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {};
    private _class = toLowerANSI _classname;
    if !(_class in (missionNamespace getVariable ["ACME_chestAccess_classes", []])) exitWith {};

    // The animation preflight reserves custody BEFORE native treatment starts. CPR and BVM are one maneuver
    // family: a swap updates the local class label but deliberately reuses the exact same patient lease ID.
    private _maneuvers = missionNamespace getVariable [
        "ACME_chestAccess_maneuverClasses",
        ["cpr","usebvm","usebvm_oxygen","usebvm_vehicleoxygen","usebvm_portableoxygen"]
    ];
    private _existing = _medic getVariable ["ACME_chestAccess_treatment", []];
    private _samePatient = (_existing param [0,objNull]) isEqualTo _patient;
    private _existingClass = _existing param [1,""];
    private _existingId = _existing param [2,""];

    if (_samePatient && {_existingId != ""} && {_existingClass == _class}) exitWith {};
    if (_samePatient && {_existingId != ""} && {_existingClass in _maneuvers} && {_class in _maneuvers}) exitWith {
        _medic setVariable ["ACME_chestAccess_treatment", [_patient, _class, _existingId]];
    };

    private _serial = (missionNamespace getVariable ["ACME_chestAccess_serial", 0]) + 1;
    missionNamespace setVariable ["ACME_chestAccess_serial", _serial];
    private _id = format ["%1:%2:%3", clientOwner, netId _medic, _serial];
    _medic setVariable ["ACME_chestAccess_treatment", [_patient, _class, _id]];
    [_patient, _medic, _id, true, _class] call ACME_fnc_chestAccessVestEvent;
}] call CBA_fnc_addEventHandler;

["ace_treatmentSucceded", {
    params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
    if (isNull _medic || {!local _medic}) exitWith {};
    private _entry = _medic getVariable ["ACME_chestAccess_treatment", []];
    if ((_entry param [0, objNull]) != _patient) exitWith {};
    private _stored = _entry param [1, ""];
    private _event = toLowerANSI _classname;
    if (_stored != _event) exitWith {};

    // Stethoscope success only launches its held scope. The continuous-action failure event below is the true end.
    if (_stored == "usestethoscope") exitWith {};

    // CPR and BVM are one continuous chest-access family. One watcher owns the stable lease across any number of
    // middle-mouse swaps. It releases only after both roles, both preflight states and both handoff windows are gone.
    if (_stored in (missionNamespace getVariable ["ACME_chestAccess_maneuverClasses", ["cpr"]])) exitWith {
        private _id = _entry param [2, ""];
        private _watch = _medic getVariable ["ACME_chestAccessManeuverWatch", []];
        if ((_watch param [0,objNull]) isEqualTo _patient && {(_watch param [1,""]) == _id}) exitWith {};

        _medic setVariable ["ACME_chestAccessManeuverWatch", [_patient, _id, _stored], false];

        [{
            params ["_p", "_m", "_id"];
            if (isNull _p || {isNull _m} || {!alive _m}) exitWith {true};

            private _watch = _m getVariable ["ACME_chestAccessManeuverWatch", []];
            if !((_watch param [0,objNull]) isEqualTo _p && {(_watch param [1,""]) == _id}) exitWith {true};

            private _handoff = _m getVariable ["ACME_chestAccessManeuverHandoff", []];
            private _handoffActive = (_handoff param [0, objNull, [objNull]]) isEqualTo _p
                && {(_handoff param [1, -1, [0]]) > CBA_missionTime};

            private _ownerHandoffUntil = _p getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
            private _ownerHandoffActive = (_ownerHandoffUntil isEqualType 0) && {serverTime < _ownerHandoffUntil};

            private _preparing = (_m getVariable ["ACME_chestAccessPreflightActive", false])
                && {((_m getVariable ["ACME_chestAccess_treatment", []]) param [0,objNull]) isEqualTo _p};

            private _maneuverActive = [_p] call ACME_fnc_chestAccessManeuverActive;

            !_maneuverActive && {!_handoffActive} && {!_ownerHandoffActive} && {!_preparing}
        }, {
            params ["_p", "_m", "_id", "_stored"];
            if (!isNull _m && {local _m}) then {
                private _watch = _m getVariable ["ACME_chestAccessManeuverWatch", []];
                if ((_watch param [0,objNull]) isEqualTo _p && {(_watch param [1,""]) == _id}) then {
                    _m setVariable ["ACME_chestAccessManeuverWatch", [], false];
                };

                private _cur = _m getVariable ["ACME_chestAccess_treatment", []];
                if ((_cur param [2, ""]) == _id) then {_m setVariable ["ACME_chestAccess_treatment", []];};

                private _handoff = _m getVariable ["ACME_chestAccessManeuverHandoff", []];
                if ((_handoff param [0, objNull, [objNull]]) isEqualTo _p) then {
                    _m setVariable ["ACME_chestAccessManeuverHandoff", [], false];
                };
            };
            if (!isNull _p) then {[_p, _m, _id, false, _stored] call ACME_fnc_chestAccessVestEvent;};
        }, [_patient, _medic, _id, _stored]] call CBA_fnc_waitUntilAndExecute;
    };

    _medic setVariable ["ACME_chestAccess_treatment", []];
    [_patient, _medic, _entry param [2, ""], false, _stored] call ACME_fnc_chestAccessVestEvent;
}] call CBA_fnc_addEventHandler;

["ace_treatmentFailed", {
    params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
    if (isNull _medic || {!local _medic}) exitWith {};
    private _entry = _medic getVariable ["ACME_chestAccess_treatment", []];
    if ((_entry param [0, objNull]) != _patient) exitWith {};
    private _stored = _entry param [1, ""];
    private _event = toLowerANSI _classname;
    private _scopeEnd = _stored == "usestethoscope" && {_event in ["usestethoscope", "acm_continuousaction"]};
    if (!_scopeEnd && {_stored != _event}) exitWith {};

    // Once a CPR/BVM maneuver watcher exists, it alone owns final release. A short setup/failure event from one
    // side of a swap must never tear down the stable lease underneath the other side.
    private _maneuvers = missionNamespace getVariable ["ACME_chestAccess_maneuverClasses", ["cpr"]];
    private _watch = _medic getVariable ["ACME_chestAccessManeuverWatch", []];
    if (_stored in _maneuvers && {(_watch param [0,objNull]) isEqualTo _patient}
        && {(_watch param [1,""]) == (_entry param [2,""])}) exitWith {};

    _medic setVariable ["ACME_chestAccess_treatment", []];
    [_patient, _medic, _entry param [2, ""], false, _stored] call ACME_fnc_chestAccessVestEvent;
}] call CBA_fnc_addEventHandler;
