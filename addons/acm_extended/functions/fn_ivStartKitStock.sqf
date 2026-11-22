/* Sealed IV Start Kits in the owner's worn inventory that hold this item, each with its own contents
   (ACME_ivStartKitContents of its class: the 14/16/18/20G kits hold catheters of their own gauge).
   Returns [[kit class, contents], ...], one entry for every such kit carried. */
params ["_unit", "_item"];
if (isNull _unit || {!local _unit} || {!alive _unit}) exitWith {[]};
private _found = [];
{
    if ((_x find "ACME_IVStartKit_") == 0) then {
        private _contents = getArray (configFile >> "CfgWeapons" >> _x >> "ACME_ivStartKitContents");
        if (_item in _contents) then {_found pushBack [_x, _contents];};
    };
} forEach (items _unit);
_found
