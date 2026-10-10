// Owner-authoritative two-phase Y-line refill transaction.
// Claim reserves one exact Y access before the medic starts ACM's native 5 s Add Bag action.
// Finalize waits for ivBagLocal to create the replacement bag on this owner, then applies Y-specific state.
params [
    ["_patient",objNull,[objNull]],
    ["_medic",objNull,[objNull]],
    ["_operation","",[""]],
    ["_requestId","",[""]],
    ["_mode","",[""]],
    ["_part","",[""]],
    ["_iv",true,[true]],
    ["_site",-1,[0]],
    ["_epoch",-1,[0]],
    ["_fromCooler",false,[false]],
    ["_warmer",false,[false]]
];
if (isNull _patient || {!local _patient} || {_requestId == ""}) exitWith {false};
_part = toLowerANSI _part;
_mode = toLowerANSI _mode;
private _key = toLowerANSI (format ["%1#%2#%3",_part,_iv,_site]);
private _claims = _patient getVariable ["ACME_yRefillClaims",createHashMap];

// A crashed/disconnected provider cannot lock a Y leg forever. Fifteen seconds covers the native 5 s progress,
// event delivery and owner-side finalize wait with ample margin.
{
    private _entry = _claims get _x;
    private _owner = _entry param [0,objNull,[objNull]];
    private _at = _entry param [3,-100,[0]];
    if (isNull _owner || {!alive _owner} || {serverTime - _at > 15}) then {_claims deleteAt _x;};
} forEach +(keys _claims);
[_patient,"ACME_yRefillClaims",_claims] call ACME_fnc_setVarNet;

private _send = {
    params ["_stage","_accepted",["_reason","",[""]]];
    if (!isNull _medic) then {
        ["ACME_yRefillResult",[_patient,_requestId,_stage,_accepted,_reason],_medic] call CBA_fnc_targetEvent;
    };
    _accepted
};
private _claimMatches = {
    private _entry = _claims getOrDefault [_key,[]];
    count _entry >= 5
        && {(_entry select 0) isEqualTo _medic}
        && {(_entry select 1) == _requestId}
        && {(_entry select 2) == _mode}
        && {(_entry select 4) == _epoch}
};

switch (_operation) do {
    case "claim": {
        if !(_mode in ["blood","saline"]) exitWith {["claim",false,"Invalid Y-line refill type."] call _send};
        if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {["claim",false,"Patient state changed. Reopen the transfusion menu."] call _send};
        if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
            || {(_medic distance _patient) > ace_medical_gui_maxDistance}) exitWith {
            ["claim",false,"Provider can no longer refill this Y line."] call _send
        };
        if !([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {
            ["claim",false,"That IV/IO access is no longer available."] call _send
        };
        private _lines = (_patient getVariable ["ACME_YLines",[]]) apply {toLowerANSI _x};
        if !(_key in _lines) exitWith {["claim",false,"That access no longer has Y tubing."] call _send};

        if ((_patient getVariable ["ACME_yFlushJobs",createHashMap]) getOrDefault [_key,[]] isNotEqualTo []) exitWith {
            ["claim",false,"Finish priming/flushing before replacing a bag on this line."] call _send
        };
        private _existing = _claims getOrDefault [_key,[]];
        if !(count _existing isEqualTo 0) exitWith {
            if (count _existing >= 5 && {(_existing select 0) isEqualTo _medic} && {(_existing select 1) == _requestId}
                && {(_existing select 2) == _mode} && {(_existing select 4) == _epoch}) exitWith {
                ["claim",true,""] call _send
            };
            ["claim",false,"Another provider is already replacing a bag on this Y line."] call _send
        };

        private _map = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
        private _arr = _map getOrDefault [_part,[]];
        private _blocked = "";
        if (_mode == "blood") then {
            private _hasBlood = (_arr findIf {
                ((_x param [0,""]) in ["Blood","FreshBlood"])
                    && {(_x param [1,0]) > 0.01}
                    && {(_x param [3,-1]) == _site}
                    && {(_x param [4,true]) isEqualTo _iv}
            }) >= 0;
            if (_hasBlood) then {_blocked = "A unit is still running on this Y line.";};
            private _dirty = (_patient getVariable ["ACME_YLineDirty",createHashMap]) getOrDefault [_key,false];
            if (_dirty) then {_blocked = "Flush the line before hanging the next unit.";};
        } else {
            private _hasReserve = (_arr findIf {
                ((_x param [0,""]) in ["ACME_SalineY","Saline"])
                    && {(_x param [1,0]) > 0.5}
                    && {(_x param [3,-1]) == _site}
                    && {(_x param [4,true]) isEqualTo _iv}
            }) >= 0;
            if (_hasReserve) then {_blocked = "This Y line already has a live saline reserve.";};
        };

        if (_blocked != "") exitWith {["claim",false,_blocked] call _send};
        _claims set [_key,[_medic,_requestId,_mode,serverTime,_epoch]];
        [_patient,"ACME_yRefillClaims",_claims] call ACME_fnc_setVarNet;
        ["claim",true,""] call _send
    };

    case "cancel": {
        if (call _claimMatches) then {
            _claims deleteAt _key;
            [_patient,"ACME_yRefillClaims",_claims] call ACME_fnc_setVarNet;
        };
        ["cancel",true,""] call _send
    };

    case "finalize": {
        if !(call _claimMatches) exitWith {["done",false,"Y-line refill reservation expired. The hung bag was left unchanged."] call _send};

        private _args = [_patient,_medic,_requestId,_mode,_part,_iv,_site,_epoch,_fromCooler,_warmer,_key];
        private _ready = {
            params ["_patient","_medic","_requestId","_mode","_part","_iv","_site","_epoch","_fromCooler","_warmer","_key"];
            if (isNull _patient || {!local _patient}) exitWith {true};
            private _claims = _patient getVariable ["ACME_yRefillClaims",createHashMap];
            private _entry = _claims getOrDefault [_key,[]];
            if (count _entry < 5 || {!((_entry select 0) isEqualTo _medic)} || {(_entry select 1) != _requestId}) exitWith {true};
            private _arr = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
            if (_mode == "blood") then {
                (_arr findIf {
                    ((_x param [0,""]) in ["Blood","FreshBlood"])
                        && {(_x param [1,0]) > 0.01}
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv}
                }) >= 0
            } else {
                (_arr findIf {
                    ((_x param [0,""]) == "Saline")
                        && {(_x param [1,0]) > 0.5}
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv}
                }) >= 0
            };
        };
        private _finish = {
            params ["_patient","_medic","_requestId","_mode","_part","_iv","_site","_epoch","_fromCooler","_warmer","_key"];
            if (isNull _patient || {!local _patient}) exitWith {};
            private _claims = _patient getVariable ["ACME_yRefillClaims",createHashMap];
            private _entry = _claims getOrDefault [_key,[]];
            if (count _entry < 5 || {!((_entry select 0) isEqualTo _medic)} || {(_entry select 1) != _requestId}) exitWith {};

            private _release = {
                _claims deleteAt _key;
                [_patient,"ACME_yRefillClaims",_claims] call ACME_fnc_setVarNet;
            };
            if ((_entry param [4,-1]) != _epoch || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
                || {isNull _medic} || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
                || {([_medic,_patient] call ACME_fnc_patientInteractionDistance) > 5}
                || {!([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) exitWith {call _release;};
            private _lines = (_patient getVariable ["ACME_YLines",[]]) apply {toLowerANSI _x};
            if !(_key in _lines) exitWith {
                call _release;
                if (!isNull _medic) then {
                    ["ACME_yRefillResult",[_patient,_requestId,"done",false,"Y tubing changed during the hang. The bag remains hung as a normal bag."],_medic] call CBA_fnc_targetEvent;
                };
            };

            private _map = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
            private _arr = +(_map getOrDefault [_part,[]]);
            private _bagIdx = -1;
            if (_mode == "blood") then {
                _bagIdx = _arr findIf {
                    ((_x param [0,""]) in ["Blood","FreshBlood"])
                        && {(_x param [1,0]) > 0.01}
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv}
                };
                _arr = _arr select {
                    !(((_x param [0,""]) == "ACME_Empty")
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv})
                };
            } else {
                _bagIdx = _arr findIf {
                    ((_x param [0,""]) == "Saline")
                        && {(_x param [1,0]) > 0.5}
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv}
                };
                if (_bagIdx >= 0) then {
                    private _uid = (_arr select _bagIdx) param [8,"",[""]];
                    for "_i" from 0 to ((count _arr)-1) do {
                        private _candidate = _arr select _i;
                        if (((_candidate param [8,"",[""]]) == _uid) && {_uid != ""}) exitWith {_bagIdx = _i;};
                    };
                    private _e = +(_arr select _bagIdx);
                    _e set [0,"ACME_SalineY"];
                    _arr set [_bagIdx,_e];
                };
                _arr = _arr select {
                    !(((_x param [0,""]) == "ACME_EmptySaline")
                        && {(_x param [3,-1]) == _site}
                        && {(_x param [4,true]) isEqualTo _iv})
                };
                private _pins = _patient getVariable ["ACME_YPins",createHashMap];
                if (_key in _pins) then {_pins deleteAt _key; _patient setVariable ["ACME_YPins",_pins,true];};
                _patient setVariable ["ACME_YPinRelease_" + _key,nil,false];
            };

            if (_bagIdx < 0) exitWith {
                call _release;
                if (!isNull _medic) then {
                    ["ACME_yRefillResult",[_patient,_requestId,"done",false,"Replacement bag could not be identified. The bag remains hung unchanged."],_medic] call CBA_fnc_targetEvent;
                };
            };

            _map set [_part,_arr];
            [_patient,_map,true] call ACME_fnc_ivBagsCommit;
            [_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags;
            [_patient,_part,_iv,_site] call ACME_fnc_resumeSiteFlow;

            if (_mode == "blood") then {
                _warmer = [_patient, _part, _iv, _site, _warmer, _medic] call ACME_fnc_lineWarmer;
                if (_warmer) then {
                    [_patient,true,false,objNull,serverTime + 15,true] call ACME_fnc_bloodThermalStateCommit;
                } else {
                    if (_fromCooler) then {
                        [_patient,false,true,serverTime,serverTime + 15,true] call ACME_fnc_bloodThermalStateCommit;
                    };
                };
                if (!isNil "ace_medical_treatment_fnc_addToLog") then {
                    [_patient,"activity","%1 replaced the blood unit on a Y line",[[_medic,false,true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
                };
            } else {
                if (!isNil "ace_medical_treatment_fnc_addToLog") then {
                    [_patient,"activity","%1 replaced the Y line saline reserve",[[_medic,false,true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
                };
            };
            call _release;
            if (!isNull _medic) then {
                ["ACME_yRefillResult",[_patient,_requestId,"done",true,""],_medic] call CBA_fnc_targetEvent;
            };
        };
        private _timeout = {
            params ["_patient","_medic","_requestId","_mode","_part","_iv","_site","_epoch","_fromCooler","_warmer","_key"];
            if (isNull _patient || {!local _patient}) exitWith {};
            private _claims = _patient getVariable ["ACME_yRefillClaims",createHashMap];
            private _entry = _claims getOrDefault [_key,[]];
            if (count _entry >= 2 && {(_entry select 0) isEqualTo _medic} && {(_entry select 1) == _requestId}) then {
                _claims deleteAt _key;
                [_patient,"ACME_yRefillClaims",_claims] call ACME_fnc_setVarNet;
            };
            if (!isNull _medic) then {
                ["ACME_yRefillResult",[_patient,_requestId,"done",false,"Y refill finalized late. The bag remains hung, but the Y-specific retag was not applied."],_medic] call CBA_fnc_targetEvent;
            };
        };
        [_ready,_finish,_args,2.5,_timeout] call CBA_fnc_waitUntilAndExecute;
        true
    };

    default {false};
};
