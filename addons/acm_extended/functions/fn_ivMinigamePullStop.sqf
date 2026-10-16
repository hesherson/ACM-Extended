// end a catheter pull.
// call it as [_done] call ACME_fnc_ivMinigamePullStop.
// _done true means the catheter came all the way out. _done false means the medic let go part way, and the
// catheter stays where it is.
params [["_done", false]];
private _idx = uiNamespace getVariable ["ACME_IV_PullIdx", -1];
private _uid=uiNamespace getVariable ["ACME_IV_PullUID",""];
private _kind=uiNamespace getVariable ["ACME_IV_PullKind","catheter"];

private _clear = {
    uiNamespace setVariable ["ACME_IV_PullIdx", -1];
    uiNamespace setVariable ["ACME_IV_PullUID",""];
    uiNamespace setVariable ["ACME_IV_PullKind","catheter"];
    uiNamespace setVariable ["ACME_IV_PullLayers",[]];
    uiNamespace setVariable ["ACME_IV_PullLayerBases",[]];
    private _extra=uiNamespace getVariable ["ACME_IV_PullExtra",controlNull];
    if (!isNull _extra) then {ctrlDelete _extra;};
    uiNamespace setVariable ["ACME_IV_PullExtra",controlNull];
    uiNamespace setVariable ["ACME_IV_PullProg", 0];
    uiNamespace setVariable ["ACME_IV_PullPin", []];
    uiNamespace setVariable ["ACME_IV_PullBroke", false];
    uiNamespace setVariable ["ACME_IV_PullCtrl", controlNull];
};

if !([] call ACME_fnc_ivUiValid) exitWith {call _clear;};
if (_idx < 0) exitWith { call _clear; };
if (!_done) exitWith {
    // part way out is not a state the model keeps. the catheter goes back to seated and the marks are redrawn.
    call _clear;
    [] call ACME_fnc_ivMinigameRenderMarks;
};

private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (isNull _patient) exitWith { call _clear; };
private _marks = _patient getVariable ["ACME_IV_Marks", []];
if (_uid!="") then {_idx=_marks findIf {(_x param [14,""])==_uid && {(_x param [4,""])=="hub"}};};
if (_idx<0 || {_idx >= count _marks}) exitWith { call _clear;[] call ACME_fnc_ivMinigameRenderMarks; };
if (_kind in ["removeLock","removeSecondary","removeExtension","removeDressing","removeLine"]) exitWith {
    call _clear;
    [0,0,_kind,_uid] call ACME_fnc_ivFinishStart;
    [] call ACME_fnc_ivMinigameRenderMarks;
};

private _mark=_marks select _idx;
private _medic=uiNamespace getVariable ["ACME_IV_Medic",ACE_player];
[_patient,"ivCatheterPull",[_medic,_mark param [14,""],[_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
call _clear;
[] call ACME_fnc_ivMinigameRenderMarks;
playSound "ACE_Sound_Click";
