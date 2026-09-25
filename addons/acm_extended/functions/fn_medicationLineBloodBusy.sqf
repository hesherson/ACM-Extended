/*
 * True only when blood is CURRENTLY flowing through the exact vascular access selected for a medication push.
 * Empty blood bags and blood bags on another IV/IO do not block medication. A closed/occluded line does not
 * count as flowing. This is read-only and safe on provider and patient-owner machines.
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

// Native line switch / roller state. If this access itself is shut, blood is not currently running through it.
private _lineOpen = if (_iv) then {
    private _flows = _patient getVariable [
        "ACM_circulation_FluidBagsFlow_IV",
        [[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]
    ];
    ((_flows param [_partIndex,[1,1,1],[[]]]) param [_site,1,[0]]) > 0
} else {
    private _flows = _patient getVariable ["ACM_circulation_FluidBagsFlow_IO", [1,1,1,1,1,1]];
    (_flows param [_partIndex,1,[0]]) > 0
};
if (!_lineOpen) exitWith {false};

// The flow-rate authority also applies AAJT/tourniquet occlusion, access gauge, clamp and pressure-cuff state.
if (([_patient,_partIndex,_iv,_site,-1,""] call ACM_circulation_fnc_getIVFlowRate) <= 0) exitWith {false};

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

private _detached = _patient getVariable ["ACME_detachedBags", []];
(_bags findIf {
    private _bag = _x;
    if !(_bag isEqualType [] && {count _bag >= 5}) exitWith {false};
    private _type = _bag param [0,"",[""]];
    private _remaining = _bag param [1,0,[0]];
    private _bagSite = _bag param [3,-1,[0]];
    private _bagIV = _bag param [4,true,[true]];
    private _bagUid = _bag param [8,"",[""]];
    (_type in ["Blood","FreshBlood"])
        && {_remaining > 0.01}
        && {_bagIV isEqualTo _iv}
        && {!_iv || {_bagSite == _site}}
        && {!(_bagUid in _detached)}
}) >= 0
