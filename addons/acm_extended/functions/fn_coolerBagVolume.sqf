/* B287: volume of a supported blood bag, independent of its blood type. */
params [["_class", "", [""]]];
if ((_class find "ACM_BloodBag_") != 0 && {(_class find "ACM_FreshBloodBag_") != 0}) exitWith {0};
private _parts = _class splitString "_";
private _suffix = _parts param [(count _parts) - 1, ""];
if !(_suffix in ["250", "500", "1000"]) exitWith {0};
parseNumber _suffix
