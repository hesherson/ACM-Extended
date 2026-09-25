/*
 * True when a NON-EMPTY blood product is attached to the exact vascular access selected for a medication push.
 * Medication is allowed only after that blood bag is empty or absent. Closing the clamp does not make the line
 * medication-safe because blood is still occupying the tubing. Blood on another IV/IO does not block this access.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_bodyPart", "", [""]],
    ["_site", -2, [0]]
];
if (isNull _patient) exitWith {false};

private _part = toLowerANSI _bodyPart;
if (_part == "ej") then {_part = "head";};
private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
private _partIndex = _parts find _part;
if (_partIndex < 0 || {!(_site in [-1,0,1,2])}) exitWith {false};
private _iv = _site >= 0;

private _bagMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if !(_bagMap isEqualType createHashMap) exitWith {false};
private _bags = _bagMap getOrDefault [_part, []];
if (_bags isEqualTo []) then {
    private _key = (keys _bagMap) select {
        _x isEqualType "" && {(toLowerANSI _x) == _part}
    } param [0,""];
    if (_key != "") then {_bags = _bagMap getOrDefault [_key,[]];};
};
if !(_bags isEqualType []) exitWith {false};

(_bags findIf {
    private _bag = _x;
    if !(_bag isEqualType [] && {count _bag >= 5}) exitWith {false};
    private _type = _bag param [0,"",[""]];
    private _remaining = _bag param [1,0,[0]];
    private _bagSite = _bag param [3,-1,[0]];
    private _bagIV = _bag param [4,true,[true]];
    (_type in ["Blood","FreshBlood","FBTK"])
        && {_remaining > 0.01}
        && {_bagIV isEqualTo _iv}
        && {!_iv || {_bagSite == _site}}
}) >= 0
