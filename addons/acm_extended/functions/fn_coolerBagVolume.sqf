/* Native fresh bags are ACME_FreshBloodBag_<volume>_<donorID>.
 * Their final numeric component is an identity, never a bag volume. */
params [["_class", "", [""]]];
if (_class=="ACME_SpoiledBlood") exitWith {500};
if ((_class find "ACME_SpoiledBlood_")==0) exitWith {parseNumber (_class select [18])};

private _standard = (_class find "ACME_BloodBag_") == 0;
if (!_standard && {(_class find "ACME_FreshBloodBag_") != 0}) exitWith {0};
private _parts = _class splitString "_";
private _volume = if (_standard) then {
    _parts param [(count _parts) - 1, ""]
} else {
    if (count _parts in [3, 4]) then {_parts param [2, ""]} else {""}
};
if !(_volume in ["250","500","1000"]) exitWith {0};
parseNumber _volume
