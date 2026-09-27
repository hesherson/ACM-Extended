// Stage 1 of the HPMK. Inventory is taken on the provider owner, while the casualty owner serializes the reusable
// kit reservation. If two providers finish Prep HPMK at nearly the same time, only the first owner-side commit wins;
// every losing provider gets the item back instead of consuming a second kit or overwriting ACME_hpmk_provider.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_inventoryTaken", false, [false]],
    ["_supplyReceipt", [], [[]]]
];
if (isNull _medic || {isNull _patient}) exitWith {false};

// Reserve once on the treating provider's machine; ACE chooses patient/provider/vehicle supply.
if (!_inventoryTaken) then {
    _supplyReceipt = [_medic, _patient, ["ACM_HPMK"]] call ACME_fnc_treatmentSupplyTake;
    _inventoryTaken = !(_supplyReceipt isEqualTo []);
};
if (!_inventoryTaken) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "hpmkPrep", [_medic, _patient, true, _supplyReceipt]] call ACME_fnc_ownerDispatch;
    true
};

// Patient-owner phase. Revalidate eligibility and state after the treatment timer, because another provider may
// have completed the same action during our progress bar.
private _lyingState = _patient getVariable ["ACM_core_Lying_State", false];
private _isLying = if (_lyingState isEqualType true) then {_lyingState} else {_lyingState > 0};
private _eligible = (_patient getVariable ["ACE_isUnconscious", false]) || {_isLying};
private _occupied = (_patient getVariable ["ACME_hpmk_state", ""]) != "";
if (!_eligible || {_occupied}) exitWith {
    ["ACME_supplySettle", [_supplyReceipt, true], parseNumber ((_supplyReceipt param [3, "0"]) splitString ":" select 0)] call CBA_fnc_ownerEvent;
    if (_occupied) then {["This patient already has an HPMK prepped or applied.", 2, _medic] call ACME_fnc_netNotice;};
    false
};

// The casualty authority accepts only one reservation. Settle on the issuer, including remote donors.
["ACME_supplySettle", [_supplyReceipt, false], parseNumber ((_supplyReceipt param [3, "0"]) splitString ":" select 0)] call CBA_fnc_ownerEvent;

_patient setVariable ["ACME_hpmk_provider", _medic, true];
_patient setVariable ["ACME_hpmk_returnPending", false, true];
[_patient, "prepped", true, false] call ACME_fnc_hpmkStateCommit;
["HPMK prepped. Wrap to begin rewarming, or remove to stow it.", 3, _medic] call ACME_fnc_netNotice;
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "activity", "NAR HPMK prepped", []] call ace_medical_treatment_fnc_addToLog;
};
true
