/* Owner-authoritative lease for shared patient/vehicle vial inventory.
 * Only one provider may mutate a non-self vial holder at a time. The lease is deliberately short and renewed by
 * normal Narc Box stock refreshes, so death/disconnect/locality loss cannot strand a shared source for long.
 * The source holder may be dead; patient life is never used as an inventory gate.
 */
params [
    ["_holder", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_op", "claim", [""]],
    ["_token", "", [""]]
];
if (isNull _holder || {_token == ""}) exitWith {};
if (!local _holder) exitWith {[_holder, "vialLease", [_medic,_op,_token]] call ACME_fnc_ownerDispatch;};
// Settle queued source deltas before an expired/released holder can grant a new
// drawer. A still-live lease leaves them queued until its release or expiry.
[_holder] call ACME_fnc_vialRefundLocal;

private _now = serverTime;
private _lease = +(_holder getVariable ["ACME_vialLease", [objNull,"",0]]);
_lease params [
    ["_leaseMedic", objNull, [objNull]],
    ["_leaseToken", "", [""]],
    ["_leaseUntil", 0, [0]]
];
private _leaseLive = !isNull _leaseMedic && {alive _leaseMedic} && {_leaseToken != ""} && {_leaseUntil > _now};

private _reachable = {
    if (isNull _medic || {!alive _medic}) exitWith {false};
    if (_holder isKindOf "CAManBase") exitWith {
        private _mv = objectParent _medic;
        private _hv = objectParent _holder;
        (!isNull _mv && {_mv isEqualTo _hv}) || {(_medic distance _holder) <= 5}
    };
    (objectParent _medic) isEqualTo _holder
};

private _accepted = false;
private _reason = "";
private _until = _leaseUntil;
switch (toLowerANSI _op) do {
    case "release": {
        if (_leaseMedic isEqualTo _medic && {_leaseToken isEqualTo _token}) then {
            _holder setVariable ["ACME_vialLease", nil, true];
            [_holder] call ACME_fnc_vialRefundLocal;
            _accepted = true;
            _until = 0;
        };
    };
    default {
        if !(call _reachable) exitWith {_reason = "Shared medication source is no longer within reach.";};
        if (!_leaseLive || {(_leaseMedic isEqualTo _medic) && {_leaseToken isEqualTo _token}}) then {
            _until = _now + 4;
            _holder setVariable ["ACME_vialLease", [_medic,_token,_until], true];
            _accepted = true;
        } else {
            _reason = "Another provider is currently drawing medication from that inventory.";
        };
    };
};

if (!isNull _medic) then {
    ["ACME_vialLeaseResult", [_holder,_token,_accepted,_until,_reason], _medic] call CBA_fnc_targetEvent;
};
