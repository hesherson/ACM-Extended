/* Called in the owner's unscheduled dispatcher. Keep the exact native event
   contract/listeners, then verify only this puncture's site within the same call. */
params ["_medic", "_patient", "_bodyPart", "_type", "_site", "_epoch", ["_receipt", []]];
if (isNull _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {
    if (_receipt isNotEqualTo []) then {["ACME_supplySettle", [_receipt, true], parseNumber ((_receipt param [3, "0"]) splitString ":" select 0)] call CBA_fnc_ownerEvent;};
};
if (!local _patient) exitWith {[_patient, "ivSite", _this] call ACME_fnc_ownerDispatch;};
if !(_bodyPart in ["head","body","leftarm","rightarm","leftleg","rightleg"]
    && {_site in [0,1,2]} && {_type in [0,1,2,5,6]}) exitWith {
    if (_receipt isNotEqualTo []) then {["ACME_supplySettle", [_receipt, true], parseNumber ((_receipt param [3, "0"]) splitString ":" select 0)] call CBA_fnc_ownerEvent;};
};
["ACM_circulation_setIVLocal", [_medic, _patient, _bodyPart, _type, true, _site]] call CBA_fnc_localEvent;
if (_type > 0) then {[_patient, _bodyPart, _site, _type, [], _epoch] call ACME_fnc_ivEnforceSite;};

if (_receipt isNotEqualTo []) then {["ACME_supplySettle", [_receipt, false], parseNumber ((_receipt param [3, "0"]) splitString ":" select 0)] call CBA_fnc_ownerEvent;};
