/* B226: fold a newly hung live bag into the matching empty Y limb. Pure array operation.
 * Preserve the live tuple (including UID), other sites, reserve volume and unrelated bags.
 * Called on the casualty owner before the native attach is published. */
params ["_bags", "_newIndex"];
private _result = +_bags;
if (_newIndex < 0 || {_newIndex >= count _result}) exitWith {_result};
private _new = _result select _newIndex;
_new params [["_type", ""], ["_remaining", 0], "", ["_site", -1], ["_iv", true]];
private _empty = switch (true) do {
    case (_type in ["Blood", "FreshBlood"] && {_remaining > 0.01}): {"ACME_Empty"};
    case (_type in ["Saline", "ACME_SalineY"] && {_remaining > 0.5}): {"ACME_EmptySaline"};
    default {""};
};
if (_empty == "") exitWith {_result};
private _matches = {
    (_this param [0, ""]) == _empty && {(_this param [3, -1]) == _site}
        && {(_this param [4, true]) isEqualTo _iv}
};
private _slot = _result findIf {_x call _matches};
if (_slot < 0) exitWith {_result};
_result = [];
{
    if (_forEachIndex == _slot) then {_result pushBack _new;};
    if (_forEachIndex != _newIndex && {!(_x call _matches)}) then {_result pushBack _x;};
} forEach _bags;
_result
