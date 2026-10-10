/* setMaxLoad is server-executed, persistent for JIP. Derive the limit from the captured vest class. */
params ["_patient", "_cargo"];
if (!isServer || {isNull _patient} || {isNull _cargo} || {typeOf _cargo != "ACME_RemovedCarrierCargo"}) exitWith {};
if (!((_patient getVariable ["ACME_carrierCargo", objNull]) isEqualTo _cargo)
    || {!((_cargo getVariable ["ACME_carrierPatient", objNull]) isEqualTo _patient)}) exitWith {};
private _savedVar = _cargo getVariable ["ACME_carrierSavedVar", ""];
if !(_savedVar in ["ACME_chestAccess_vestLoadout", "ACME_CS_vestLoadout", "ACME_headElev_vestLoadout"]) exitWith {};
private _class = (_patient getVariable [_savedVar, []]) param [0, ""];
private _containerClass = getText (configFile >> "CfgWeapons" >> _class >> "ItemInfo" >> "containerClass");
private _limit = getNumber (configFile >> "CfgVehicles" >> _containerClass >> "maximumLoad");
if (_limit > 0) then {_cargo setMaxLoad _limit;};
