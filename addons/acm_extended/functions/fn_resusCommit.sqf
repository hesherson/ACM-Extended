/* One patient-owner writer for multiplayer CPR/BVM reservations, toggles, releases and delivered breaths.
 * Separate slots permit one compressor and one ventilator. Native mechanical ventilation owns its patient sentinel.
 */
params [["_patient",objNull,[objNull]],["_args",[],[[]]],["_serverVerified",false,[false]],["_verifiedAt",-1,[0]],["_hops",0,[0]]];
if (canSuspend) exitWith {
    private _answer=false;
    isNil {_answer=[_patient,_args,_serverVerified,_verifiedAt,_hops] call ACME_fnc_resusCommit;};
    _answer
};
if (isNull _patient || {count _args != 10} || {!finite _hops} || {_hops < 0} || {_hops > 4}) exitWith {false};
_args params [["_op","",[""]],["_kind","",[""]],["_medic",objNull,[objNull]],["_token","",[""]],
    ["_epoch",-1,[0]],["_providerOwner",-1,[0]],["_locality",-1,[0]],["_nativeEpoch",-1,[0]],["_sentAt",-1,[0]],["_payload",[],[[]]]];
if (!(_kind in ["cpr","bvm"]) || {!(_op in ["claim","activate","start","toggle","oxygen","breath","telemetry","release"])}
    || {isNull _medic} || {_token == ""} || {!finite _epoch} || {_epoch < 0}
    || {!finite _providerOwner} || {_providerOwner < 0} || {_providerOwner != floor _providerOwner}
    || {!finite _locality} || {_locality < 0} || {_locality != floor _locality}
    || {!finite _nativeEpoch} || {_nativeEpoch < 0} || {_nativeEpoch != floor _nativeEpoch}
    || {!finite _sentAt}) exitWith {false};
// owner(object) is server-only. A remote provider on a client-owned patient must first pass
// the server's current ownership check. Never refresh the request/breath's original issue time.
if (isMultiplayer && {!isServer} && {!local _medic} && {!_serverVerified}) exitWith {
    ["ACME_resusValidate",[_patient,_args,false,-1,_hops]] call CBA_fnc_serverEvent;
    false
};
if (isMultiplayer && {isServer} && {_op != "release"} && {_providerOwner != owner _medic}) exitWith {false};
if (_serverVerified && {_op != "release"} && {(!finite _verifiedAt || {serverTime-_verifiedAt > 2} || {_verifiedAt-serverTime > 0.5})}) exitWith {false};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        ["ACME_resusCommit",[_patient,_args,true,if (isServer) then {serverTime} else {_verifiedAt},_hops+1],_patient] call CBA_fnc_targetEvent;
    };
    false
};
private _key = "ACME_resus_" + _kind;
private _row = _patient getVariable [_key,[]];
if (!(_row isEqualType []) || {count _row != 11}
    || {!((_row select 0) isEqualType objNull)} || {!((_row select 1) isEqualType "")}
    || {!((_row select 7) isEqualType false)}
    || {([2,3,4,5,6,8,9,10] findIf {!((_row select _x) isEqualType 0) || {!finite (_row select _x)}}) >= 0}) then {_row=[];};
private _prefix = ["ACM_circulation_CPR","ACM_breathing_BVM"] select (_kind == "bvm");
private _sessionKey = _prefix + "_session";
private _medicKey = _prefix + "_Medic";
private _providerKey = ["ace_medical_CPR_provider","ACM_breathing_BVM_provider"] select (_kind == "bvm");
private _providerField = ["cprProvider","bvmProvider"] select (_kind == "bvm");
private _medicField = ["cprMedic","bvmMedic"] select (_kind == "bvm");
private _sessionField = ["cprSession","bvmSession"] select (_kind == "bvm");
private _setNative = {
    params ["_field","_value"];
    if (_kind == "cpr") then {[_patient,[[_field,_value]],true] call ACM_circulation_fnc_setRuntimeState}
    else {[_patient,[[_field,_value]],true] call ACM_breathing_fnc_setRuntimeState};
};
private _retire = {
    params ["_captured"];
    private _holder = _captured param [0,objNull];
    private _episode = _captured param [5,-1];
    if ((_patient getVariable [_sessionKey,[]]) isEqualTo [_holder,_episode]) then {
        if ((_patient getVariable [_providerKey,objNull]) isEqualTo _holder) then {[_providerField,objNull] call _setNative;};
        if ((_patient getVariable [_medicKey,objNull]) isEqualTo _holder) then {[_medicField,objNull] call _setNative;};
        [_sessionField,[]] call _setNative;
        if (_kind == "bvm" && {(_patient getVariable [_providerKey,objNull]) isEqualTo objNull}) then {
            ["bvmConnectedOxygen",false] call _setNative;
        };
    };
    _patient setVariable [_key,[],true];
};
private _matches = count _row == 11 && {(_row select 0) isEqualTo _medic}
    && {(_row select 1) == _token} && {(_row select 2) == _epoch}
    && {(_row select 3) == _providerOwner} && {(_row select 4) == _locality}
    && {(_row select 5) == _nativeEpoch};
if (_op == "release") exitWith {
    if (_epoch == ([_patient] call ACME_fnc_clinicalEpoch) && {_token != ""}) then {
        [_patient,"resus:"+_kind,_medic,_token,_epoch,"cancel"] call ACME_fnc_actionClaimLedger;
    };
    if (_matches) then {
        if (_kind == "cpr" && {(_row select 8) >= 0}) then {
            ["cprStoppedTotal",(serverTime-(_row select 9)) max 0] call _setNative;
            ["cprStoppedTime",CBA_missionTime] call _setNative;
        };
        [_row] call _retire;
    };
    _matches
};
private _available = alive _medic && {[_medic] call ace_common_fnc_isAwake}
    && {[_medic,_patient] call ACME_fnc_patientInteractionContact}
    && {if (local _medic) then {_providerOwner == clientOwner} else {!isServer || {_providerOwner == owner _medic}}}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {!(_patient getVariable ["ACME_clinicalRestoring",false])};
if (_op == "claim") exitWith {
    private _reason = [_patient,_medic,_epoch,_providerOwner,_sentAt] call ACME_fnc_actionClaimValidate;
    if (_reason == "" && {_kind == "bvm"} && {(_patient getVariable [_providerKey,objNull]) isEqualTo _patient}) then {_reason="mechanical-ventilation-active";};
    if (_reason == "" && {!_available}) then {_reason = "treatment-contact";};
    if (_reason == "" && {_kind == "cpr"} && {alive _patient} && {[_patient] call ace_common_fnc_isAwake}) then {_reason = "patient-awake";};
    if (_reason == "" && {_kind == "bvm"} && {!([_medic,_patient,true] call ACM_breathing_fnc_canUseBVM)}) then {_reason = "patient-awake";};
    if (_reason == "" && {(!finite _locality || {_locality < 0} || {_locality != floor _locality}
        || {!finite _nativeEpoch} || {_nativeEpoch < 0} || {_nativeEpoch != floor _nativeEpoch} || {_token == ""})}) then {_reason = "episode-invalid";};
    private _oldValid = false;
    if (count _row == 11) then {
        private _oldMedic = _row select 0;
        _oldValid = !isNull _oldMedic && {alive _oldMedic} && {[_oldMedic] call ace_common_fnc_isAwake}
            && {(_row select 2) == ([_patient] call ACME_fnc_clinicalEpoch)}
            && {(_row select 7) || {serverTime < (_row select 6)}}
            && {[_oldMedic,_patient] call ACME_fnc_patientInteractionContact}
            && {if (local _oldMedic) then {(_row select 3) == clientOwner} else {!isServer || {(_row select 3) == owner _oldMedic}}};
        if (!_oldValid) then {[_row] call _retire; _row=[];};
    };
    private _cached = [_patient,"resus:"+_kind,_medic,_token,_epoch,"lookup"] call ACME_fnc_actionClaimLedger;
    private _fresh = (_cached select 0) == "new";
    private _legacy = _patient getVariable [_medicKey,objNull];
    private _legacyValid = if (_kind == "cpr") then {[_legacy,_patient] call ACM_circulation_fnc_cprSessionValid}
        else {[_legacy,_patient] call ACM_breathing_fnc_bvmSessionValid};
    private _accepted = _reason == "" && {
        if (_fresh) then {!_oldValid && {!_legacyValid}} else {(_cached select 0) == "accepted" && {_matches && {_oldValid}}}
    };
    private _until = if (_fresh) then {serverTime + 10} else {(_cached select 2) param [0,-1]};
    if (_fresh) then {
        private _saved = [_patient,"resus:"+_kind,_medic,_token,_epoch,["reject","accept"] select _accepted,0,[_until]] call ACME_fnc_actionClaimLedger;
        _accepted = _accepted && {(_saved select 0) == "accepted"};
    };
    if (_accepted && {_fresh}) then {
        _row = [_medic,_token,_epoch,_providerOwner,_locality,_nativeEpoch,_until,false,-1,-1,-1];
        _patient setVariable [_key,_row,true];
        [_medicField,_medic] call _setNative;
        [_sessionField,[_medic,_nativeEpoch]] call _setNative;
        if (_kind == "cpr") then {[_providerField,objNull] call _setNative;};
    };
    private _request = [_kind,_patient,_token,_epoch,_providerOwner,_locality,_nativeEpoch,+_payload,_sentAt+10];
    ["ACME_resusAck",[_patient,_medic,_request,_accepted,_until,_reason],_medic] call CBA_fnc_targetEvent;
    _accepted
};
private _eligible = if (_kind == "cpr") then {!alive _patient || {!([_patient] call ace_common_fnc_isAwake)}} else {
    [_medic,_patient,true] call ACM_breathing_fnc_canUseBVM
};
if (_matches && {!_eligible}) exitWith {[_row] call _retire;false;};
if (!_matches || {!_available} || {!finite _sentAt} || {serverTime-_sentAt > 5} || {_sentAt-serverTime > 0.5}) exitWith {false};
if (!(_row select 7) && {serverTime >= (_row select 6)}) exitWith {[_row] call _retire; false};
switch (_op) do {
    case "activate": {
        if (_row select 7) exitWith {};
        if (_kind == "bvm" && {(_patient getVariable [_providerKey,objNull]) isEqualTo _patient}) exitWith {[_row] call _retire;};
        _row set [7,true];
        _patient setVariable [_key,_row,true];
        if (_kind == "bvm") then {
            [_providerField,_medic] call _setNative;
            ["bvmConnectedOxygen",_payload param [0,false,[false]]] call _setNative;
        };
    };
    case "start": {
        if (_kind == "cpr" && {(_row select 8) < 0} && {(!alive _patient || {!([_patient] call ace_common_fnc_isAwake)})}) then {
            _row set [7,true];
            _row set [8,CBA_missionTime];
            _row set [9,serverTime];
            _patient setVariable [_key,_row,true];
            [_providerField,_medic] call _setNative;
            [_patient,CBA_missionTime,+_row] call ACM_circulation_fnc_handleCPR;
        };
    };
    case "toggle": {
        if (_row select 7) then {
            private _active = (_patient getVariable [_providerKey,objNull]) isEqualTo _medic;
            // Preserve the ventilator sentinel if an external machine took this clinical channel.
            if (_active || {isNull (_patient getVariable [_providerKey,objNull])}) then {
                [_providerField,[objNull,_medic] select (!_active)] call _setNative;
            };
        };
    };
    case "oxygen": {if (_kind == "bvm" && {(_patient getVariable [_providerKey,objNull]) isEqualTo _medic}) then {["bvmConnectedOxygen",_payload param [0,false,[false]]] call _setNative;};};
    case "breath": {
        _payload params [["_oxygen",false,[false]],["_sequence",-1,[0]]];
        if (_kind == "bvm" && {_row select 7} && {(_patient getVariable [_providerKey,objNull]) isEqualTo _medic}
            && {finite _sequence} && {_sequence > (_row select 9)} && {_sequence == floor _sequence}
            && {(_row select 10) < 0 || {serverTime - (_row select 10) >= 4}}) then {
            _row set [9,_sequence]; _row set [10,serverTime];
            _patient setVariable [_key,_row,true];
            private _changes = [["bvmLastBreath",CBA_missionTime]];
            if (_oxygen && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false]}) then {_changes pushBack ["bvmLastBreathOxygen",CBA_missionTime];};
            [_patient,_changes,true] call ACM_breathing_fnc_setRuntimeState;
            _patient setVariable ["ACME_bvm_lastBreathServer",serverTime,true];
        };
    };
    case "telemetry": {
        private _rate = _payload param [0,0,[0]];
        if (_kind == "bvm" && {_row select 7} && {(_patient getVariable [_providerKey,objNull]) isEqualTo _medic}
            && {finite _rate} && {_rate >= 0} && {_rate <= 80} && {serverTime-(_row select 10) < 10}) then {
            [_patient,"ACME_bvm_rate",_rate] call ACME_fnc_setVarNet;
        };
    };
};
true
