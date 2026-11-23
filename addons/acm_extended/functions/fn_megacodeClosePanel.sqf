/* Idempotent Megacode panel teardown. */
params ["_display"];
private _pfh=uiNamespace getVariable ["ACME_MC_tickPFH",-1];
if (_pfh>=0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_MC_tickPFH",-1];

{if (!isNull _x) then {ctrlDelete _x;};} forEach (uiNamespace getVariable ["ACME_MC_contentCtrls",[]]);
uiNamespace setVariable ["ACME_MC_contentCtrls",[]];
// Dynamic panel controls are destroyed with the display; clear references so no later call touches stale handles.
{uiNamespace setVariable [_x,nil];} forEach [
    "ACME_MC_dynamicCtrls","ACME_MC_navCtrls","ACME_MC_traceCtrls","ACME_MC_laneCenters","ACME_MC_vitalCtrls",
    "ACME_MC_waveBuffers","ACME_MC_waveSig","ACME_MC_geometry","ACME_MC_step","ACME_MC_stepAcc","ACME_MC_lastT",
    "ACME_MC_statusCtrl","ACME_MC_pageSig","ACME_MC_sigCheckT"
];

private _dummy=uiNamespace getVariable ["ACME_MC_target",objNull];
private _previous=uiNamespace getVariable ["ACME_MC_previousAEDTarget",objNull];
if ((missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target",objNull]) isEqualTo _dummy) then {
    [[["aedMonitorTarget", _previous]]] call ACM_circulation_fnc_setLocalUiState;
};
uiNamespace setVariable ["ACME_MC_previousAEDTarget",objNull];
uiNamespace setVariable ["ACME_Megacode_DLG",displayNull];

private _op=uiNamespace getVariable ["ACME_MC_operator",objNull];
if (!isNull _op) then {
    private _tok=(_op getVariable ["ACME_MC_animTok",0])+1;
    _op setVariable ["ACME_MC_animTok",_tok,false];
    [_op,"Acts_Kore_TalkingOverRadio_out"] call ACME_fnc_doAnim;
    [{
        params ["_u","_t"];
        if (isNull _u || {!local _u} || {!alive _u} || {(_u getVariable ["ACME_MC_animTok",-1]) != _t}) exitWith {};
        if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};
        _u switchMove "";
        _u setUnitPos "AUTO";
    },[_op,_tok],1.0] call CBA_fnc_waitAndExecute;
};
