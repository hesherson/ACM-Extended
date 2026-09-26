// Keep the placement gesture immediate; reserve the item locally and commit on the server.
params ["_idx"];
private _holes = uiNamespace getVariable ["ACME_CS_Holes", []];
if (_idx < 0 || {_idx >= count _holes}) exitWith {};
private _hole = _holes select _idx;
if (_hole select 4) exitWith {};
private _key = [_hole] call ACME_fnc_chestSealKey;
if !(["seal", _key, "ACM_ChestSeal"] call ACME_fnc_chestSealRequest) exitWith {};
(_holes select _idx) set [4, true];
uiNamespace setVariable ["ACME_CS_Holes", _holes];
uiNamespace setVariable ["ACME_CS_Held", false];
private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
uiNamespace setVariable ["ACME_CS_SealsLeft", [_medic, "ACM_ChestSeal"] call ace_common_fnc_getCountOfItem];
// The exact AinvPknlMstpSnonWrflDnon_medic3 motion is presentation only: the item/state transaction above has
// already committed. Give each placement its own generation so Flip, Close, or a newer placement can preempt this
// animation without an older delayed callback later reclaiming the provider.
private _applySerial = (uiNamespace getVariable ["ACME_CS_ApplyGestureSerial",0]) + 1;
uiNamespace setVariable ["ACME_CS_ApplyGestureSerial",_applySerial];

// Hand the persistent workspace (or an earlier placement) directly into the newest finite placement.
if (!isNull _medic && {local _medic}) then {
    private _patient = uiNamespace getVariable ["ACME_CS_Patient",objNull];
    private _pose = _medic getVariable ["ACME_treatmentPoseState",[]];
    private _workspaceEpoch = _medic getVariable ["ACME_CS_providerHoldEpoch",-1];

    private _poseMode = _pose param [1,""];
    private _poseEpoch = _pose param [0,-1];
    if (_poseEpoch >= 0 && {_poseMode in ["chestSealWorkspace","chestSeal"]}) then {
        [_medic,_poseMode,_poseEpoch,true] call ACME_fnc_treatmentPoseStop;
    };

    _medic setVariable ["ACME_CS_providerHoldEpoch",-1,false];
    uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",-1];

    private _placeEpoch = [_medic,"chestSeal",2.0,_patient] call ACME_fnc_treatmentPoseStart;
    uiNamespace setVariable ["ACME_CS_ApplyGestureUntil",diag_tickTime + 2.0];

    [{
        params ["_m","_p","_epoch","_serial"];
        if ((uiNamespace getVariable ["ACME_CS_ApplyGestureSerial",-1]) != _serial) exitWith {};
        if (isNull _m || {!local _m}) exitWith {};
        private _state = _m getVariable ["ACME_treatmentPoseState",[]];
        if ((_state param [0,-2]) == _epoch && {(_state param [1,""]) == "chestSeal"}) then {
            [_m,"chestSeal",_epoch,true] call ACME_fnc_treatmentPoseStop;
        };

        uiNamespace setVariable ["ACME_CS_ApplyGestureUntil",0];
        private _display = uiNamespace getVariable ["ACME_CS_DLG",displayNull];
        if (!isNull _display
            && {(uiNamespace getVariable ["ACME_CS_Medic",objNull]) isEqualTo _m}
            && {(uiNamespace getVariable ["ACME_CS_Patient",objNull]) isEqualTo _p}) then {
            private _holdEpoch = [_m,_p] call ACME_fnc_chestSealProviderHoldStart;
            _m setVariable ["ACME_CS_providerHoldEpoch",_holdEpoch,false];
            uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",_holdEpoch];
        };
    }, [_medic,_patient,_placeEpoch,_applySerial], 2.0] call CBA_fnc_waitAndExecute;
};

[] call ACME_fnc_chestSealRefreshSlot;
[] call ACME_fnc_chestSealRender;
[] call ACME_fnc_chestSealPrompt;
