/* Patient-owner atomic Direct Pressure site claim.
 * One body part can have only one provider reservation at a time. The reservation survives temporary clinical
 * yielding (CPR/BVM/treatment animation) and is released only by the owning Direct Pressure episode or reconciliation.
 */
params [["_patient",objNull,[objNull]],["_op","claim",[""]],["_args",[],[[]]]];
if (isNull _patient || {!local _patient}) exitWith {};

_args params [
    ["_medic",objNull,[objNull]],
    ["_part","",[""]],
    ["_token","",[""]],
    ["_epoch",-1,[0]],
    ["_providerOwner",-1,[0]],
    ["_sentAt",-1,[0]]
];
_part = toLowerANSI _part;
if (!(_part in ["head","body","leftarm","rightarm","leftleg","rightleg"]) || {_token == ""}) exitWith {};

private _claimKey = format ["ACME_DP_claim_%1",_part];
private _pressKey = format ["ACME_DP_press_%1",_part];
private _claim = _patient getVariable [_claimKey,[]];
private _scope = "dp:" + _part;

if (_op == "release") exitWith {
    [_patient,_scope,_medic,_token,_epoch,"cancel"] call ACME_fnc_actionClaimLedger;
    private _owns = (_claim isEqualType []) && {count _claim >= 4}
        && {(_claim select 0) isEqualTo _medic}
        && {(_claim select 1) == _token}
        && {(_claim select 2) == _epoch};
    if (_owns) then {
        _patient setVariable [_claimKey,[],true];
        if ((_patient getVariable [_pressKey,objNull]) isEqualTo _medic) then {
            _patient setVariable [_pressKey,objNull,true];
        };
        if ((_patient getVariable ["ACME_DP_TorsoMedic",objNull]) isEqualTo _medic) then {
            _patient setVariable ["ACME_DP_TorsoMedic",objNull,true];
        };
        if ((_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo _medic) then {
            _patient setVariable ["ACME_DP_LimbMedic",objNull,true];
        };
        if (_part in ["leftarm","rightarm","leftleg","rightleg"]) then {
            [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
        };
    };
};

if (_op != "claim" || {isNull _medic}) exitWith {};

private _currentMedic = _claim param [0,objNull,[objNull]];
private _currentToken = _claim param [1,"",[""]];
private _currentEpoch = _claim param [2,-1,[0]];
private _currentOwner = _claim param [3,-1,[0]];
private _currentAt = _claim param [4,-1,[0]];
private _currentOwnerValid = !isNull _currentMedic
    && {_currentOwner > 0 || {_currentOwner == 0 && {!isMultiplayer} && {local _currentMedic}}}
    && {if (local _currentMedic) then {_currentOwner == clientOwner} else {
        isMultiplayer && {!isServer || {_currentOwner == owner _currentMedic}}
    }};
private _currentActive = !isNull _currentMedic
    && {_currentOwnerValid}
    && {_currentMedic getVariable ["ACME_DP_Active",false]}
    && {(_currentMedic getVariable ["ACME_DP_ClaimToken",""]) == _currentToken}
    && {(_currentMedic getVariable ["ACME_DP_ClaimEpoch",-1]) == _currentEpoch}
    && {(_currentMedic getVariable ["ACME_DP_Patient",objNull]) isEqualTo _patient}
    && {toLowerANSI (_currentMedic getVariable ["ACME_DP_Part",""]) == _part};
private _currentPending = !isNull _currentMedic
    && {_currentAt >= 0}
    && {(serverTime - _currentAt) <= 3}
    && {_currentOwnerValid};
private _currentValid = !isNull _currentMedic
    && {alive _currentMedic}
    && {!(_currentMedic getVariable ["ACE_isUnconscious",false])}
    && {_currentEpoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {_currentActive || {_currentPending}};

// A dead/disconnected/stale holder never blocks the next provider.
if (!_currentValid && {!isNull _currentMedic || {!(_claim isEqualTo [])}}) then {
    _patient setVariable [_claimKey,[],true];
    if ((_patient getVariable [_pressKey,objNull]) isEqualTo _currentMedic) then {
        _patient setVariable [_pressKey,objNull,true];
    };
    // Before a new claim is granted, restore generic marker and bleeding state
    // for this expired provider without modifying another medic's marker.
    if ((_patient getVariable ["ACME_DP_TorsoMedic",objNull]) isEqualTo _currentMedic) then {
        _patient setVariable ["ACME_DP_TorsoMedic",objNull,true];
    };
    if ((_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo _currentMedic) then {
        _patient setVariable ["ACME_DP_LimbMedic",objNull,true];
    };
    if (_part in ["leftarm","rightarm","leftleg","rightleg"]) then {
        [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
    };
    _claim = [];
    _currentMedic = objNull;
    _currentToken = "";
};

private _reason = [_patient,_medic,_epoch,_providerOwner,_sentAt] call ACME_fnc_actionClaimValidate;
if (_reason == "" && {(_medic distance _patient) > ((missionNamespace getVariable ["ACME_DP_torsoLeashDist",3.2]) max (missionNamespace getVariable ["ACME_DP_leashDist",2.7]))}) then {_reason = "out-of-range";};
if (_reason == "" && {!(missionNamespace getVariable ["ACME_sys_dp",true])}) then {_reason = "system-disabled";};
private _validRequest = _reason == "";
private _cached = [_patient,_scope,_medic,_token,_epoch,"lookup"] call ACME_fnc_actionClaimLedger;
private _fresh = (_cached select 0) == "new";
private _accepted = _validRequest && {
    if (_fresh) then {isNull _currentMedic || {_currentMedic isEqualTo _medic}} else {
        (_cached select 0) == "accepted" && {_currentValid}
        && {_currentMedic isEqualTo _medic} && {_currentToken == _token}
    }
};
if (!_accepted && {_reason == ""}) then {
    _reason = if (_fresh) then {"site-busy"} else {
        switch (_cached select 0) do {
            case "cancelled": {"request-cancelled"};
            case "blocked": {"claim-capacity"};
            case "rejected": {(_cached select 2) param [2,"request-rejected"]};
            default {"claim-stale"};
        }
    };
};
// The first grant fixes the activation deadline. Duplicate requests cannot renew a pending reservation.
private _grantedAt = serverTime;
private _grantUntil = if (_fresh) then {_grantedAt + 3} else {(_cached select 2) param [1,-1]};
if (_fresh) then {
    private _stored = [_patient,_scope,_medic,_token,_epoch,["reject","accept"] select _accepted,0,[_accepted,_grantUntil,_reason]] call ACME_fnc_actionClaimLedger;
    if (_accepted && {(_stored select 0) != "accepted"}) then {_reason = "claim-capacity";};
    _accepted = _accepted && {(_stored select 0) == "accepted"};
};
// A duplicate claim returns the same decision without refreshing reservation age or reinstating a yielded marker.
if (_accepted && {_fresh}) then {
    _patient setVariable [_claimKey,[_medic,_token,_epoch,_providerOwner,_grantedAt],true];
    // Reserve the clinical slot immediately. Activation on the provider follows the ACK.
    _patient setVariable [_pressKey,_medic,true];
    if (_part == "body") then {
        _patient setVariable ["ACME_DP_TorsoMedic",_medic,true];
    } else {
        _patient setVariable ["ACME_DP_LimbMedic",_medic,true];
    };
    if (_part in ["leftarm","rightarm","leftleg","rightleg"]) then {
        [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
    };
};

// Address the provider object, including after a locality change. The local reply handler checks the original
// requesting machine and episode before activation, releasing only this token if the request has gone stale.
["ACME_directPressureClaimAck",[_patient,_medic,_part,_token,_accepted,_epoch,_providerOwner,_grantUntil,_reason],_medic] call CBA_fnc_targetEvent;
