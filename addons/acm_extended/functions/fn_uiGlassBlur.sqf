/* Menu-owned local scene blur. Chromium cannot sample the Arma world behind its surface.
   The PP pass affects the 3D scene, including outside panels; it does not blur UI text. */
params ["_display",["_acquire",true]];
if (!hasInterface) exitWith {};
private _users = (uiNamespace getVariable ["ACME_glassBlurUsers",[]]) select {
    !isNull _x && {_x getVariable ["ACME_glassBlurActive",false]}
};
if (!isNull _display) then {
    _display setVariable ["ACME_glassBlurActive",_acquire];
    if (_acquire) then {_users pushBackUnique _display;} else {_users = _users - [_display];};
};
uiNamespace setVariable ["ACME_glassBlurUsers",_users];
private _handle = uiNamespace getVariable ["ACME_glassBlurHandle",-1];
if (_users isEqualTo [] || {(uiNamespace getVariable ["ACME_NV_FocusHandle",-1]) >= 0}) exitWith {
    if (_handle >= 0) then {ppEffectDestroy _handle;};
    uiNamespace setVariable ["ACME_glassBlurHandle",-1];
};
if (_handle < 0 && {diag_tickTime >= (uiNamespace getVariable ["ACME_glassBlurRetry",0])}) then {
    for "_i" from 0 to 7 do {
        _handle = ppEffectCreate ["DynamicBlur",17510 + _i];
        if (_handle >= 0) exitWith {};
    };
    uiNamespace setVariable ["ACME_glassBlurRetry",diag_tickTime + 2];
    if (_handle >= 0) then {
        _handle ppEffectEnable true;
        _handle ppEffectForceInNVG true;
        _handle ppEffectAdjust [0.35];
        _handle ppEffectCommit 0;
        uiNamespace setVariable ["ACME_glassBlurHandle",_handle];
    };
};
