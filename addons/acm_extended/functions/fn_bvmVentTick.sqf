// the BVM ventilation visual cue. B90 does not modify ACM BVM execution. This file passively observes ACM's native next-breath timestamp and paints the accessibility cue without writing provider/action/animation state.
// a geometry note: in arma the normalized unit is the screen height for both axes, because x spans 0 to the aspect
// ratio, so a control with w numerically equal to h is pixel-square. the circle therefore stays round on any
// display, the 32:9 ultrawide included. it is centerd at the safezone center.

if !(missionNamespace getVariable ["ACME_sys_bvm", true]) exitWith {};  // system toggle: fully off means this stops
private _layer = "ACME_BVMVent" call BIS_fnc_rscLayer;
private _dlg = uiNamespace getVariable ["ACME_BVMVent_DLG", displayNull];

// the setting is off, so ensure the layer is down and bail.
if !(missionNamespace getVariable ["ACME_a11y_bvmVentCircle", true]) exitWith {
    if (!isNull _dlg) then { _layer cutText ["", "PLAIN"]; };
};

private _player = ACE_player;

private _patient = if (!isNull _player && {alive _player}) then {
    [_player] call ACME_fnc_bvmVisualPatient
} else {objNull};

if (isNull _patient) exitWith {
    if (!isNull _dlg) then { _layer cutText ["", "PLAIN"]; };
    uiNamespace setVariable ["ACME_bvmVent_t0", -1e9];
    uiNamespace setVariable ["ACME_bvmVent_lastNativeNextBreath", -1];
};

// ensure the layer is up.
if (isNull _dlg) then {
    _layer cutRsc ["ACME_BVMVent_Display", "PLAIN", 0, false];
    _dlg = uiNamespace getVariable ["ACME_BVMVent_DLG", displayNull];
};
if (isNull _dlg) exitWith {};
private _ctrl = _dlg displayCtrl 71511;
if (isNull _ctrl) exitWith {};

// Passive observation only. B90 leaves BVM execution completely native ACM. ACM advances its local
// BVM_NextBreath timestamp in the same branch that plays bvm_squeeze.wav, so a change in that timestamp is our
// read-only cue that a squeeze just occurred. No BVM provider/action/animation state is written by ACME here.
private _now = diag_tickTime;
private _nextBreath = missionNamespace getVariable ["ACM_breathing_BVM_NextBreath", -1];
private _lastNext = uiNamespace getVariable ["ACME_bvmVent_lastNativeNextBreath", -1];
private _t0 = uiNamespace getVariable ["ACME_bvmVent_t0", -1e9];
if (_nextBreath > 0 && {_nextBreath != _lastNext}) then {
    _t0 = _now;
    uiNamespace setVariable ["ACME_bvmVent_lastNativeNextBreath", _nextBreath];
    uiNamespace setVariable ["ACME_bvmVent_t0", _t0];
};

// the pulse shape.
private _Di    = missionNamespace getVariable ["ACME_a11y_bvmVentInflateSec", 1.23];
private _Dc    = missionNamespace getVariable ["ACME_a11y_bvmVentCollapseSec", 0.35];  // fast collapse
private _baseD = missionNamespace getVariable ["ACME_a11y_bvmVentBaseSize", 0.05];  // default diameter (screen-h frac)
private _peakD = missionNamespace getVariable ["ACME_a11y_bvmVentPeakSize", 0.085];  // peak diameter
private _grow  = _peakD - _baseD;

private _t = _now - _t0;
private _D = _baseD;
private _alpha = 0;
if (_t < _Di) then {
    private _k = _t / (_Di max 0.0001);
    _k = _k * _k * (3 - 2 * _k);  // smoothstep ease
    _D = _baseD + (_grow * _k);
    _alpha = 0.20 + (0.55 * _k);  // 20% -> 75%
} else {
    if (_t < (_Di + _Dc)) then {
        private _k = (_t - _Di) / (_Dc max 0.0001);
        _k = _k * _k * (3 - 2 * _k);
        _D = _peakD - (_grow * _k);  // peak -> default (fast)
        _alpha = 0.75 * (1 - _k);  // 75% -> 0
    } else {
        _D = _baseD;
        _alpha = 0;  // idle between ventilations
    };
};

// apply it, round and centerd.
private _x = safezoneX + (safezoneW / 2) - (_D / 2);
private _y = safezoneY + (safezoneH / 2) - (_D / 2);
_ctrl ctrlSetPosition [_x, _y, _D, _D];
_ctrl ctrlSetTextColor (["info", _alpha] call ACME_fnc_a11yColor);
_ctrl ctrlCommit 0;
