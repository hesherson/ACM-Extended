/* B213 active observation. Every callback is tied to its own epoch; prep never consumes watch seconds. */
disableSerialization;
params ["_args", "_pfh"];
_args params ["_epoch"];
private _session = uiNamespace getVariable ["ACME_RespirationSession", []];
if (_session isEqualTo [] || {(_session select 0) != _epoch}) exitWith {
    [_pfh] call CBA_fnc_removePerFrameHandler;
};
_session params ["", "_medic", "_patient", "_poseEpoch", "", "_watch", "_breathAt", "_created", "_vehicle"];
private _display = uiNamespace getVariable ["ACME_RespirationDisplay", displayNull];
private _now = diag_tickTime;
private _quit = isNull _medic || {isNull _patient} || {!local _medic}
    || {_medic isNotEqualTo ACE_player} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {objectParent _medic isNotEqualTo _vehicle} || {objectParent _patient isNotEqualTo _vehicle}
    || {isNull _vehicle && {_medic distance2D _patient > ace_medical_gui_maxDistance}}
    || {isNull _display}
    || {_now - _created > 0.20 && {dialog || {!isNull (uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull])}}};
if (_quit) exitWith {[false, false, _epoch] call ACME_fnc_respirationStop;};

private _ready = !isNull _vehicle;
private _superseded = false;
private _successor = false;
if (isNull _vehicle) then {
    private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
    _superseded = (_pose param [0, -2]) != _poseEpoch || {(_pose param [1, ""]) != "pulse"};
    _successor = _superseded && {_pose isNotEqualTo []};
    _ready = !_superseded && {(_pose param [3, -1]) >= (if ((_pose param [11, -1]) >= 0) then {3} else {2})};
};
if (_superseded) exitWith {
    // A holster failure can retire our own pose without installing a successor. That must release pressure;
    // only an actual replacement pose/native treatment may keep the newer provider's busy reservation.
    _successor = _successor || {(_medic getVariable ["ACME_providerTreatmentEpoch", 0]) != (_session param [12, 0])};
    [false, !_successor, _epoch, _successor, !_successor] call ACME_fnc_respirationStop;
};
if (!_ready) exitWith {
    if (_now - _created >= 6) then {
        [false, true, _epoch] call ACME_fnc_respirationStop;
        ["Respiration measurement could not start.", 2, _medic] call ace_common_fnc_displayTextStructured;
    };
};
private _rate = [_patient] call ACME_fnc_respirationRate;
if (_watch isEqualTo []) then {
    _watch = [_now, _now, 0, 0, _rate];
    _session set [5, _watch];
};
([_watch, _now, _rate] call ACME_fnc_respirationStep) params ["_nextWatch", "_breaths", "_elapsed", "_complete"];
_session set [5, _nextWatch];
if (_breaths > 0) then {_breathAt = _now; _session set [6, _breathAt];};
private _seconds = floor _elapsed;
private _secondsText = (if (_seconds < 10) then {"0"} else {""}) + str _seconds;
(_display displayCtrl 71594) ctrlSetText format ["00:%1 / 00:15", _secondsText];

// Same PAA, color, smoothstep inflation/collapse and sizes as the existing BVM blue-circle cue.
private _inflate = missionNamespace getVariable ["ACME_a11y_bvmVentInflateSec", 1.23];
private _collapse = missionNamespace getVariable ["ACME_a11y_bvmVentCollapseSec", 0.35];
private _base = missionNamespace getVariable ["ACME_a11y_bvmVentBaseSize", 0.05];
private _peak = missionNamespace getVariable ["ACME_a11y_bvmVentPeakSize", 0.085];
// Preserve one visible rise/fall per breath even at high rates instead of restarting an unfinished inflation.
private _cycle = 60 / (_rate max 1);
private _scale = (0.90 * _cycle / ((_inflate + _collapse) max 0.01)) min 1;
_inflate = (_inflate * _scale) max 0.01;
_collapse = (_collapse * _scale) max 0.01;
private _age = _now - _breathAt;
private _diameter = _base;
private _alpha = 0;
if (_age < _inflate) then {
    private _k = (_age / _inflate) max 0;
    _k = _k * _k * (3 - 2 * _k);
    _diameter = _base + (_peak - _base) * _k;
    _alpha = 0.20 + 0.55 * _k;
} else {
    if (_age < _inflate + _collapse) then {
        private _k = (_age - _inflate) / _collapse;
        _k = _k * _k * (3 - 2 * _k);
        _diameter = _peak - (_peak - _base) * _k;
        _alpha = 0.75 * (1 - _k);
    };
};
private _circle = _display displayCtrl 71593;
_circle ctrlSetPosition [safezoneX + safezoneW / 2 - _diameter / 2, safezoneY + safezoneH / 2 - _diameter / 2, _diameter, _diameter];
_circle ctrlSetTextColor (["info", _alpha] call ACME_fnc_a11yColor);
_circle ctrlCommit 0;
if (_complete) then {
    // The stopwatch/count freeze at exactly 15. Let a breath at that boundary finish its visible blue cue
    // before teardown; otherwise the last counted breath would never be shown at all.
    if ((_session param [11, -1]) < 0) then {
        _session set [11, _now max (_breathAt + _inflate + _collapse)];
        (_display displayCtrl 71595) ctrlSetText "Observation complete";
    };
    if (_now >= (_session select 11)) then {[true, true, _epoch] call ACME_fnc_respirationStop;};
};
