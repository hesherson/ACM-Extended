/* Describe matching sealed kits in the owner's worn inventory. */
params ["_unit", "_item"];
if (isNull _unit || {!local _unit} || {!alive _unit}) exitWith {[[], []]};
private _contents = getArray (configFile >> "CfgWeapons" >> "ACME_IVStartKit_18g" >> "ACME_ivStartKitContents");
if !(_item in _contents) exitWith {[[], []]};
private _kits = (items _unit) select {(_x find "ACME_IVStartKit_") == 0};
[_contents, _kits]
