/* Three-page navigation: Transfuse <-> Narc Box <-> Body Map. */
disableSerialization;
params [["_dir","right",[""]]];
private _draw = findDisplay 84000;
private _tx = findDisplay 86000;
// Only the actual foreground workspace may request a page handoff. Repeated
// clicks after close must not fall back to a self-patient open.
if (isNull _draw && {isNull _tx}) exitWith {false};
private _patient = objNull;
private _part = "leftarm";
private _current = "transfuse";

if (!isNull _draw) then {
    _patient = uiNamespace getVariable ["ACME_SK_Patient",objNull];
    if (isNull _patient) then {_patient = _draw getVariable ["ACME_SK_ReturnPatient",objNull];};
    _part = uiNamespace getVariable ["ACME_SK_BodyPart","leftarm"];
    if (_part == "") then {_part = "leftarm";};
    _current = if ((uiNamespace getVariable ["ACME_SK_View","syringe"]) == "body") then {"body"} else {"syringe"};
} else {
    if (!isNull _tx) then {
        _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
        _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
    };
};
if (isNull _patient) then {_patient = ACE_player;};

private _target = switch (_current) do {
    case "syringe": {if (_dir == "left") then {"transfuse"} else {"body"}};
    case "body": {if (_dir == "left") then {"syringe"} else {"transfuse"}};
    default {if (_dir == "left") then {"body"} else {"syringe"}};
};

// Narc Box <-> Body Map is a true in-place page switch.
if (!isNull _draw && {_target in ["syringe","body"]}) exitWith {
    uiNamespace setVariable ["ACME_SK_View",_target];
    if (_target == "body") then {
        private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
        if !(_store isEqualTo []) then {[_store] call ACME_fnc_skSelectedIndex;};
        uiNamespace setVariable ["ACME_SK_CarouselExpanded",false];
        uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",0];
    };
    call ACME_fnc_skSetView;
};

// A single source display owns a single deferred transition. Its callback is
// invalidated if another page request supersedes it before the next frame.
private _source = if (!isNull _draw) then {_draw} else {_tx};
if (_source getVariable ["ACME_pageTransitionPending",false]) exitWith {true};
_source setVariable ["ACME_pageTransitionPending",true];
private _transitionEpoch = (uiNamespace getVariable ["ACME_pageTransitionEpoch",0]) + 1;
uiNamespace setVariable ["ACME_pageTransitionEpoch",_transitionEpoch];

private _openPage = {
    params ["_p","_part","_epoch","_requestedView","_source","_retry","_attempt"];
    if ((uiNamespace getVariable ["ACME_pageTransitionEpoch",-1]) != _epoch) exitWith {};
    private _liveDraw = findDisplay 84000;
    private _liveTx = findDisplay 86000;
    if (!isNull _liveDraw || {!isNull _liveTx}) exitWith {
        // Listen-server dialog teardown can lag the next-frame callback. Retry
        // only the exact closing source, never a newly opened workspace.
        private _sameSource = (isNull _liveDraw || {_liveDraw isEqualTo _source})
            && {isNull _liveTx || {_liveTx isEqualTo _source}};
        if (_sameSource && {_attempt < 20}) then {
            [_retry,[_p,_part,_epoch,_requestedView,_source,_retry,_attempt + 1],0.05] call CBA_fnc_waitAndExecute;
        } else {
            if (_sameSource) then {_source setVariable ["ACME_pageTransitionPending",false];};
        };
    };
    if (_requestedView == "transfuse") exitWith {
        [ACE_player,_p,_part] call ACM_circulation_fnc_openTransfusionMenu;
    };
    // A recently closed Syringe Draw may still own ACM's continuous-action
    // lock until its next PFH tick. Retire that exact closed-dialog controller
    // through its normal cleanup, so it cannot reject this page's open. Leave
    // every live hold and any newer generation alone.
    private _controller = missionNamespace getVariable ["ACM_core_ContinuousAction_Controller",[]];
    if (_controller isEqualType [] && {count _controller == 6}
        && {(_controller select 0) isEqualTo ACE_player}
        && {(_controller select 2) == (missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",-1])}
        && {(_controller select 3) isEqualType {}}
        && {(_controller select 4) isEqualType []}
        && {((_controller select 4) param [8,-1]) == 84000}) then {
        [ACE_player,[["shouldReopen",false]],false] call ACM_core_fnc_setContinuousActionState;
        [_controller select 4,_controller select 5] call (_controller select 3);
    };
    uiNamespace setVariable ["ACME_SK_RequestedView",_requestedView];
    // Clear again on the next frame so an unload handler from the previous dialog cannot restore stale prep state
    // between the button click and creation of the normal Narc Box.
    ACME_infusion_pendingContext = nil;
    missionNamespace setVariable ["ACME_infusion_bagTally", []];
    [uiNamespace getVariable ["ACME_SK_CurSize",10],_p,_part] call ACME_fnc_skOpenDraw;
};

if (_target == "transfuse") then {
    uiNamespace setVariable ["ACME_SK_suppressReturn",true];
} else {
    // Normal page opens never inherit the temporary syringe-into-bag editor.
    uiNamespace setVariable ["ACME_SK_RequestedView",_target];
    ACME_infusion_pendingContext = nil;
    missionNamespace setVariable ["ACME_infusion_bagTally", []];
};
closeDialog 0;
[_openPage,[_patient,_part,_transitionEpoch,_target,_source,_openPage,0]] call CBA_fnc_execNextFrame;
