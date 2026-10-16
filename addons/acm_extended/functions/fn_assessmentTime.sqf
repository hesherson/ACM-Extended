/* B218: normal-speed authored work plus the actual reserved entry window. The progress
 * adapter follows observed completion; no animation coefficient is fitted to a clinical timer. */
params [["_classname", "CheckAirway", [""]], ["_medic", objNull, [objNull]]];
private _speed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> "AinvPknlMstpSnonWnonDr_medic4" >> "speed");
if (!finite _speed || {_speed == 0}) exitWith {
    diag_log "[ACME ASSESSMENT] Missing medic4 duration; refusing an unknown assessment timer.";
    0
};
private _duration = if (_speed < 0) then {-_speed} else {1 / _speed};
if ((toLowerANSI _classname) == "checkairway") then {_duration = _duration + 1.75;};
if (!isNull _medic && {isNull objectParent _medic}) then {
    private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
    if ((_pose param [1, ""]) in ["assessmentAirway", "assessmentBreathing"]) then {
        private _stage = _pose param [3, 0];
        if (_stage in [-1, -2]) then {
            _duration = _duration + (((_pose param [8, CBA_missionTime]) - CBA_missionTime) max 0);
        };
        // The weapon stow has not yet entered the stand-to-kneel transition.
        if (_stage == -1 && {stance _medic == "STAND"}) then {
            private _kneelSpeed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon" >> "speed");
            private _kneel = if (_kneelSpeed < 0) then {-_kneelSpeed} else {if (_kneelSpeed > 0) then {1 / _kneelSpeed} else {0.65}};
            _duration = _duration + _kneel;
        };
    };
};
_duration
