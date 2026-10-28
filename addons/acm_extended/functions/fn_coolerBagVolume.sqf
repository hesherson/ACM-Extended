/* Native fresh bags are ACM_FreshBloodBag_<volume>_<donorID>.
 * Their final numeric component is an identity, never a bag volume. */
params [["_class", "", [""]]];
private _parts = _class splitString "_";
private _volume = "";
if ((_class find "ACM_BloodBag_") == 0) then {
    _volume = _parts param [(count _parts) - 1, ""];
};
if ((_class find "ACM_FreshBloodBag_") == 0 && {count _parts in [3,4]}) then {
    _volume = _parts param [2,""];
};
if !(_volume in ["250","500","1000"]) exitWith {0};
parseNumber _volume
