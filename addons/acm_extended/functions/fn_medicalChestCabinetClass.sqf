/* The drawer unit class a chest shows while it is open: its own variable, else its class, else eight drawers.
   Arguments: 0: closed chest (or its Eden entity). Returns: class name. */
params ["_chest"];
private _class = _chest getVariable ["ACME_medicalChestCabinetClass", getText (configOf _chest >> "acmeChestCabinetClass")];
if (_class isEqualType "" && {isClass (configFile >> "CfgVehicles" >> _class)}
    && {_class isKindOf ["ACME_MedicalChest8Drawers", configFile >> "CfgVehicles"]}) exitWith {_class};
"ACME_MedicalChest8Drawers"
