/* B391: what a confused player sees, every frame on their own client: a gentle swim of the picture (blur that
 * comes and goes) and a slight sway. Lighter than obtundation (fn_obtundedTick.sqf), which replaces it. */
private _p = if (!isNil "ACE_player" && {!isNull ACE_player}) then {ACE_player} else {player};
private _on = !isNull _p && {alive _p} && {_p getVariable ["ACME_confused", false]}
    && {!(_p getVariable ["ACME_obtunded", false])} && {!(_p getVariable ["ACE_isUnconscious", false])}
    && {isNull curatorCamera};
private _db = uiNamespace getVariable ["ACME_confused_blur", -1];
if (!_on) exitWith {
    if (_db isEqualType 0 && {_db >= 0}) then {
        _db ppEffectEnable false;
        ppEffectDestroy _db;
        uiNamespace setVariable ["ACME_confused_blur", -1];
    };
};
if !(_db isEqualType 0 && {_db >= 0}) then {
    _db = ppEffectCreate ["DynamicBlur", 817];   // ACE uses 813-815, obtundation 816
    _db ppEffectEnable true;
    uiNamespace setVariable ["ACME_confused_blur", _db];
    uiNamespace setVariable ["ACME_confused_swayNext", 0];
};
private _cycle = missionNamespace getVariable ["ACME_confused_blurCycle", 6];
private _peak = missionNamespace getVariable ["ACME_confused_blurPeak", 0.45];
private _phase = (diag_tickTime mod _cycle) / _cycle;
private _w = (sin (_phase * 360)) max 0;
_db ppEffectAdjust [_peak * _w * _w];
_db ppEffectCommit 0;
if (diag_tickTime >= (uiNamespace getVariable ["ACME_confused_swayNext", 0])) then {
    uiNamespace setVariable ["ACME_confused_swayNext", diag_tickTime + 3 + random 3];
    addCamShake [0.6, 2.5, 0.8];
};
