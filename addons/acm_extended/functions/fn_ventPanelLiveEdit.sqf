// the live screen, in edit mode: the dial changes the value of the currently selected field, the BPM or the vt. it is
// called from the knob when editing is active, and _dir is already reversed by the caller.
params ["_dir"];
if !([ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {};
private _vTgt = uiNamespace getVariable ["ACME_vent_target", ACE_player]; if (isNull _vTgt) then { _vTgt = ACE_player; };
private _selIdx = uiNamespace getVariable ["ACME_vent_selIdx", 0];
// Recheck at the mutation boundary, including a setting toggle between frames.
if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])}) && {_selIdx != 0}) exitWith {
    uiNamespace setVariable ["ACME_vent_editing", false];
};
switch (_selIdx) do {
    case 0: {  // BPM
        private _current = if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])})) then {
            ([_vTgt] call ACME_fnc_ventEffectiveSettings) select 2
        } else {uiNamespace getVariable ["ACME_vent_bpm", 12]};
        private _v = _current + _dir;
        _v = _v max 4 min 60;
        uiNamespace setVariable ["ACME_vent_bpm", _v];
        _vTgt setVariable ["ACME_vent_bpm", _v, true];
    };
    case 1: {  // VT in volume-control modes; PInsp/PIP in SIMV PC.
        private _mode = _vTgt getVariable ["ACME_vent_mode", "SIMV VC PS"];
        if (_mode == "SIMV PC") then {
            private _peep = _vTgt getVariable ["ACME_vent_peep", 5];
            private _floor = 11 max (_peep + 1);
            private _v = (uiNamespace getVariable ["ACME_vent_pinsp", (_vTgt getVariable ["ACME_vent_pinsp", 20])]) + _dir;
            _v = _v max _floor min 60;
            uiNamespace setVariable ["ACME_vent_pinsp", _v];
            _vTgt setVariable ["ACME_vent_pinsp", _v, true];
        } else {
            private _v = (uiNamespace getVariable ["ACME_vent_vt", 500]) + (_dir * 10);
            _v = _v max 50 min 1500;
            uiNamespace setVariable ["ACME_vent_vt", _v];
            _vTgt setVariable ["ACME_vent_vt", _v, true];
        };
    };
};
[] call ACME_fnc_ventPanelRefresh;
