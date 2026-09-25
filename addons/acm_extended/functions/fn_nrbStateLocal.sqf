params ["_patient", "_medic", "_on", ["_hasO2", false], ["_quiet", false], ["_oxygenSource", objNull]];
if (isNull _patient || {!local _patient}) exitWith {};
if (_on && {_patient getVariable ["ACME_nrb_on", false]}) exitWith {
    ["NRB is already on this patient.", 2, _medic] call ACME_fnc_netNotice;
};
if (_on && {!([_patient] call ACME_fnc_nrbAirwayCompatible)}) exitWith {
    ["Cannot apply NRB with an advanced airway in place. Use BVM or ventilator support.", 3, _medic] call ACME_fnc_netNotice;
};
if (!_on && {!(_patient getVariable ["ACME_nrb_on", false])}) exitWith {};
[_patient, _on, (_on && _hasO2), false, true, false] call ACME_fnc_nrbStateCommit;
_patient setVariable ["ACME_nrb_lastO2Uptake", nil, true];
_patient setVariable ["ACME_nrb_lastSpontaneousO2Breath", nil, true];
_patient setVariable ["ACME_nrb_nextBreathMark", CBA_missionTime, false];
_patient setVariable ["ACME_nrb_lastTickLocal", CBA_missionTime, false];
_patient setVariable ["ACME_nrb_sfxWanted", _on && _hasO2, false];
_patient setVariable ["ACME_nrb_drawPending", [], true];
_patient setVariable ["ACME_nrb_o2Pending", 0, true];
if (_on) then {
    ACME_NA2_sequence = (missionNamespace getVariable ["ACME_NA2_sequence", 0]) + 1;
    private _session = format ["%1:%2:%3:%4", clientOwner, netId _patient, CBA_missionTime, ACME_NA2_sequence];
    _patient setVariable ["ACME_nrb_session", _session, true];
    _patient setVariable ["ACME_nrb_drawSeq", 0, true];
    _patient setVariable ["ACME_nrb_medic", _medic, true];
    _patient setVariable ["ACME_nrb_oxygenSource", if (isNull _oxygenSource) then {_medic} else {_oxygenSource}, true];
    _patient setVariable ["ACME_nrb_nextO2", CBA_missionTime, true];
    [_patient] call ACME_fnc_ownerRegister;
    if (_hasO2) then {
        [format ["NRB applied. O2 %1 L/min.", missionNamespace getVariable ["ACME_nrb_flowLPM", 15]], 2.5, _medic] call ACME_fnc_netNotice;
        [_patient, "activity", "Non-rebreather mask applied (high-flow O2)", "NRB applied, 15 lpm", []] call ACME_fnc_medLog;
    } else {
        [_patient, "activity", "NRB placed without oxygen source", "NRB placed, no O2 source, room air", []] call ACME_fnc_medLog;
    };
} else {
    _patient setVariable ["ACME_nrb_session", "", true];
    _patient setVariable ["ACME_nrb_oxygenSource", objNull, true];
    ACME_nrb_activePatients = (missionNamespace getVariable ["ACME_nrb_activePatients", []]) - [_patient];
    if (!_quiet) then {
        ["NRB removed.", 2, _medic] call ACME_fnc_netNotice;
        [_patient, "activity", "Non-rebreather mask removed", "NRB removed", []] call ACME_fnc_medLog;
    };
};
["ACME_nrbSound", [_patient, _on && _hasO2]] call CBA_fnc_serverEvent;
