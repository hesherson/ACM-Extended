/* Install named protocol handlers once. Binding results remain machine-local diagnostic data. */
if (missionNamespace getVariable ["ACME_NA3_clinicalInstalled", false]) exitWith {};
ACME_NA3_clinicalInstalled = true;
ACME_clinical_ownedUnits = allUnits select {local _x && {alive _x}};
ACME_clinical_activePatients = [];
ACME_rhythm_activePatients = [];
["ACME_infusionAck", {[{ _this call ACME_fnc_infusionAck; }, _this] call CBA_fnc_execNextFrame;}] call CBA_fnc_addEventHandler;
["ACME_piAck", {_this call ACME_fnc_pressureInfuserAck;}] call CBA_fnc_addEventHandler;
["ACME_preparedAck", {_this call ACME_fnc_preparedAttachAck;}] call CBA_fnc_addEventHandler;
["ACME_preparedHangResult", {_this call ACME_fnc_preparedHangResult;}] call CBA_fnc_addEventHandler;
// Retry only identified, unacknowledged attachments. The reusable pressure infuser never changes inventory state.
[{
    private _cuffs = missionNamespace getVariable ["ACME_piPending", createHashMap];
    {
        private _r = _cuffs get _x;
        if (_r select 3) then {if (CBA_missionTime - (_r select 2) > 60) then {_cuffs deleteAt _x;}; continue;};
        private _patient = _r select 0;
        // Deletion also removes any committed cuff. There is no inventory refund because the infuser is never consumed.
        if (isNull _patient) then {[_x, false, false, "Patient deleted. The pending pressure-infuser request was cancelled."] call ACME_fnc_pressureInfuserAck;}
        else {[_patient, "pressureCuff", _r select 1] call ACME_fnc_ownerDispatch;};
    } forEach keys _cuffs;
    private _injections = missionNamespace getVariable ["ACME_infusionPending", createHashMap];
    {
        private _r = _injections get _x;
        if (_r select 4) then {if (CBA_missionTime - (_r select 3) > 60) then {_injections deleteAt _x;}; continue;};
        private _p = _r select 0;
        if (isNull _p) then {[_x, false] call ACME_fnc_infusionAck;} else {[_p, "infusionRegister", _r select 1] call ACME_fnc_ownerDispatch;};
    } forEach keys _injections;
    private _pending = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
    {
        private _v = _pending get _x;
        if (_v select 2) then {if (CBA_missionTime - (_v select 1) > 60) then {_pending deleteAt _x;}; continue;};
        private _args = _v select 0; private _patient = _args select 1;
        if (isNull _patient) then {[_x, false, ""] call ACME_fnc_preparedAttachAck; continue;};
        // Epoch travels in the original request identity and is stored separately below on first send.
        private _epoch = _v param [3, [_patient] call ACME_fnc_clinicalEpoch];
        [_patient, "preparedAttach", [_args, _x, _epoch]] call ACME_fnc_ownerDispatch;
    } forEach keys _pending;
    private _hangPending = missionNamespace getVariable ["ACME_preparedHangPending", createHashMap];
    {
        private _r = _hangPending get _x;
        if (_r param [3, false]) then {
            if (CBA_missionTime - (_r param [2, CBA_missionTime]) > 60) then {_hangPending deleteAt _x;};
            continue;
        };
        private _target = _r param [0, objNull];
        private _args = _r param [1, []];
        if (isNull _target) then {
            [_x, false, "Patient deleted. The prepared set was not consumed."] call ACME_fnc_preparedHangResult;
        } else {
            [_target, "preparedHang", _args] call ACME_fnc_ownerDispatch;
        };
    } forEach keys _hangPending;
}, 2, []] call CBA_fnc_addPerFrameHandler;

["ACME_clinicalNotice", {_this call ACME_fnc_clinicalNotice;}] call CBA_fnc_addEventHandler;
if (isServer) then {
    ["ACME_clinicalChestRestore", {
        params ["_p", "_rows", "_epoch"];
        if (isNull _p || {_epoch != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
        private _allowed = ["ACME_CS_holeData", "ACME_CS_wastedSeals", "ACME_ncd_placed", "ACME_ncd_tensionBase", "ACME_penetratingTorso", "ACME_penetratingTorsoCount", "ACME_thora_outputMl", "ACME_thora_outputPerHour", "ACME_thora_outputStart"];
        {
            _x params ["_key", "_value"];
            if !(_key in _allowed) then {continue;};
            switch (_key) do {
                case "ACME_thora_outputMl": {[_p, "ml", _value, true] call ACME_fnc_thoraOutputStateCommit;};
                case "ACME_thora_outputPerHour": {[_p, "perHour", _value, true] call ACME_fnc_thoraOutputStateCommit;};
                case "ACME_thora_outputStart": {[_p, "start", _value, true] call ACME_fnc_thoraOutputStateCommit;};
                default {_p setVariable [_key, _value, true];};
            };
        } forEach _rows;
        _p setVariable ["ACME_CS_netEpoch", "", true];
        _p setVariable ["ACME_CS_sealRevisions", createHashMap, true];
        [_p] call ACME_fnc_chestSealBumpVer;
    }] call CBA_fnc_addEventHandler;
};
[{
    ACME_NA3_bindingResult = call ACME_fnc_clinicalBindings;

}, [], 1] call CBA_fnc_waitAndExecute;
