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
uiNamespace setVariable ["ACME_CS_SealsLeft", [_medic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACM_ChestSeal"] call ACME_fnc_treatmentSupplyCount];
// The exact AinvPknlMstpSnonWrflDnon_medic3 motion is reserved ONLY for physically applying a seal.
// Hand the persistent workspace pose directly into that finite placement, then return directly to hands-on-chest.
if (!isNull _medic && {local _medic}) then {
    private _patient = uiNamespace getVariable ["ACME_CS_Patient",objNull];
    private _pose = _medic getVariable ["ACME_treatmentPoseState",[]];
    private _workspaceEpoch = _medic getVariable ["ACME_CS_providerHoldEpoch",-1];

    if ((_pose param [1,""]) == "chestSealWorkspace" && {_workspaceEpoch >= 0}) then {
        [_medic,"chestSealWorkspace",_workspaceEpoch,true] call ACME_fnc_treatmentPoseStop;
    };

    _medic setVariable ["ACME_CS_providerHoldEpoch",-1,false];
    uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",-1];

    private _placeEpoch = [_medic,"chestSeal",2.0,_patient] call ACME_fnc_treatmentPoseStart;
    uiNamespace setVariable ["ACME_CS_ApplyGestureUntil",diag_tickTime + 2.0];

    [{
        params ["_m","_p","_epoch"];
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
    }, [_medic,_patient,_placeEpoch], 2.0] call CBA_fnc_waitAndExecute;
};

[] call ACME_fnc_chestSealRefreshSlot;
[] call ACME_fnc_chestSealRender;
[] call ACME_fnc_chestSealPrompt;
