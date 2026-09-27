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
    ["_providerOwner",-1,[0]]
];
_part = toLowerANSI _part;
if (_part == "" || {_token == ""}) exitWith {};

private _claimKey = format ["ACME_DP_claim_%1",_part];
private _pressKey = format ["ACME_DP_press_%1",_part];
private _claim = _patient getVariable [_claimKey,[]];

if (_op == "release") exitWith {
    private _owns = (_claim isEqualType []) && {count _claim >= 4}
        && {(_claim select 0) isEqualTo _medic}
        && {(_claim select 1) == _token};
    if (_owns || {_claim isEqualTo [] && {(_patient getVariable [_pressKey,objNull]) isEqualTo _medic}}) then {
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
private _currentActive = !isNull _currentMedic
    && {_currentMedic getVariable ["ACME_DP_Active",false]}
    && {(_currentMedic getVariable ["ACME_DP_Patient",objNull]) isEqualTo _patient}
    && {toLowerANSI (_currentMedic getVariable ["ACME_DP_Part",""]) == _part};
private _currentPending = !isNull _currentMedic
    && {_currentAt >= 0}
    && {(serverTime - _currentAt) <= 3}
    && {_currentOwner == owner _currentMedic};
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
    _claim = [];
    _currentMedic = objNull;
    _currentToken = "";
};

private _validRequest = alive _medic
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {_providerOwner == owner _medic}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {(_medic distance _patient) <= ((missionNamespace getVariable ["ACME_DP_torsoLeashDist",3.2]) max (missionNamespace getVariable ["ACME_DP_leashDist",2.7]))}
    && {missionNamespace getVariable ["ACME_sys_dp",true]};

private _accepted = _validRequest && {isNull _currentMedic || {_currentMedic isEqualTo _medic}};
if (_accepted) then {
    _patient setVariable [_claimKey,[_medic,_token,_epoch,_providerOwner,serverTime],true];
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

["ACME_directPressureClaimAck",[_patient,_medic,_part,_token,_accepted,_epoch,_providerOwner],_providerOwner] call CBA_fnc_ownerEvent;
