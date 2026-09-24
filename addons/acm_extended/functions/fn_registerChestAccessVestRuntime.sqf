// Temporary plate-carrier removal for actions that need a genuinely unobstructed chest while a backpack is worn.
// This is deliberately class-exact. CPR and every explicit BVM treatment variant now share the same carrier custody
// so middle-mouse CPR <-> BVM handoffs cannot re-dress the casualty between maneuvers.
private _maneuverClasses = ["cpr", "usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"];
private _classes = ["usestethoscope", "checkbreathing", "acme_inspectchest"] + _maneuverClasses;
missionNamespace setVariable ["ACME_chestAccess_classes", _classes];
missionNamespace setVariable ["ACME_chestAccess_maneuverClasses", _maneuverClasses];

["ace_treatmentStarted", {
    params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
    if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {};
    private _class = toLowerANSI _classname;
    if !(_class in (missionNamespace getVariable ["ACME_chestAccess_classes", []])) exitWith {};

    // The animation preflight reserves custody BEFORE native treatment starts. If this exact provider/patient/class
    // already owns a lease, keep it; treatmentStarted must not remove the carrier twice or create a second owner.
    private _existing = _medic getVariable ["ACME_chestAccess_treatment", []];
    if ((_existing param [0,objNull]) isEqualTo _patient
        && {(_existing param [1,""]) == _class}
        && {(_existing param [2,""]) != ""}) exitWith {};

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

    // CPR and BVM are one continuous chest-access family. Keep the original lease until neither role is active.
    // A provider-local handoff token bridges the deliberate BVM -> CPR 0.1 s swap delay; if the replacement
    // maneuver fails to start, the token expires and ordinary restoration proceeds.
    if (_stored in (missionNamespace getVariable ["ACME_chestAccess_maneuverClasses", ["cpr"]])) exitWith {
        [{
            params ["_p", "_m", "_id"];
            if (isNull _p || {isNull _m} || {!alive _m}) exitWith {true};

            private _handoff = _m getVariable ["ACME_chestAccessManeuverHandoff", []];
            private _handoffActive = (_handoff param [0, objNull, [objNull]]) isEqualTo _p
                && {(_handoff param [1, -1, [0]]) > CBA_missionTime};
            private _maneuverActive = ([_p] call ACM_core_fnc_cprActive)
                || {[_p] call ACM_core_fnc_bvmActive};

            !_maneuverActive && {!_handoffActive}
        }, {
            params ["_p", "_m", "_id", "_stored"];
            if (!isNull _m && {local _m}) then {
                private _cur = _m getVariable ["ACME_chestAccess_treatment", []];
                if ((_cur param [2, ""]) == _id) then {_m setVariable ["ACME_chestAccess_treatment", []];};

                private _handoff = _m getVariable ["ACME_chestAccessManeuverHandoff", []];
                if ((_handoff param [0, objNull, [objNull]]) isEqualTo _p) then {
                    _m setVariable ["ACME_chestAccessManeuverHandoff", [], false];
                };
            };
            if (!isNull _p) then {[_p, _m, _id, false, _stored] call ACME_fnc_chestAccessVestEvent;};
        }, [_patient, _medic, _entry param [2, ""], _stored], 600, {
            params ["_p", "_m", "_id", "_stored"];
            if (!isNull _p) then {[_p, _m, _id, false, _stored] call ACME_fnc_chestAccessVestEvent;};
        }] call CBA_fnc_waitUntilAndExecute;
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
    _medic setVariable ["ACME_chestAccess_treatment", []];
    [_patient, _medic, _entry param [2, ""], false, _stored] call ACME_fnc_chestAccessVestEvent;
}] call CBA_fnc_addEventHandler;
