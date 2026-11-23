/* B395: the server side of IV stands (fn_ivStandInit.sqf).
 * "request" [stand, casualty, attach, requester, limb]: hang that limb's running bag on a free hook, or take it down.
 * "watch" []: every second, take down bags whose casualty died, was moved (or whose stand was dragged) out of the
 *             line's reach, or whose bag ran dry, and keep the casualty's gravity boost (ACME_hang_flowMult) up while
 *             a bag of theirs hangs.
 * A stand has two hooks, one each side of the pole: stand variables ACME_ivStand_slots [casualty or objNull, x2] and
 * ACME_ivStand_parts [limb or "", x2] (public). A casualty may have a bag on each hook (two limbs). The server's
 * list ACME_ivStand_hung [[stand, hook, casualty, jip, limb], ...] still knows a casualty after its stand is gone.
 * The casualty: ACME_hang_Stand (a stand holding one of its bags, public), ACME_hang_StandParts (its hung limbs,
 * public) and ACME_hang_flowMult, the same boost a held bag gives (fn_hangBagClaimLocal.sqf keeps it while a stand
 * holds a bag). */
if (!isServer) exitWith {};
params ["_mode", ["_args", []]];
private _boost = ((missionNamespace getVariable ["ACME_hang_flowMult", 1.75]) max 1) min 5;
private _leash = missionNamespace getVariable ["ACME_hang_leash", 3];
private _sources = ["Bag1_Hide", "Bag2_Hide"];

private _fnc_patientState = {
    // the casualty's own record of its hung limbs, from the server list
    params ["_patient"];
    if (isNull _patient) exitWith {};
    private _mine = ACME_ivStand_hung select {(_x select 2) isEqualTo _patient};
    _patient setVariable ["ACME_hang_StandParts", _mine apply {_x select 4}, true];
    if (_mine isEqualTo []) then {
        _patient setVariable ["ACME_hang_Stand", objNull, true];
        private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
        if (isNull _holder || {!alive _holder} || {!(_holder getVariable ["ACME_hang_Active", false])}) then {
            _patient setVariable ["ACME_hang_flowMult", 1, true];
        };
    } else {
        _patient setVariable ["ACME_hang_Stand", (_mine select 0) select 0, true];
        if ((_patient getVariable ["ACME_hang_flowMult", 1]) != _boost) then {_patient setVariable ["ACME_hang_flowMult", _boost, true];};
    };
};

private _fnc_clear = {
    params ["_stand", "_slot", "_patient", "_why", ["_jip", ""]];
    ACME_ivStand_hung = ACME_ivStand_hung select {!((_x select 0) isEqualTo _stand && {(_x select 1) == _slot})};
    if (!isNull _stand) then {
        private _slots = +(_stand getVariable ["ACME_ivStand_slots", [objNull, objNull]]);
        private _parts = +(_stand getVariable ["ACME_ivStand_parts", ["", ""]]);
        _slots set [_slot, objNull];
        _parts set [_slot, ""];
        _stand setVariable ["ACME_ivStand_slots", _slots, true];
        _stand setVariable ["ACME_ivStand_parts", _parts, true];
        // the stand's own decorative bag comes back as it was
        private _phases = _stand getVariable ["ACME_ivStand_decor", []];
        if ((count _phases) > _slot) then {_stand animateSource [_sources select _slot, _phases select _slot, true];};
    };
    [_patient] call _fnc_patientState;
    ["ACME_ivStandVisual", [_stand, _slot, objNull, false, _jip]] call CBA_fnc_globalEvent;
    if (_jip != "") then {[_jip] call CBA_fnc_removeGlobalEventJIP;};
    if (_why != "" && {call ACME_fnc_debugEnabled}) then {diag_log text format ["[ACME] IV stand: bag of %1 taken down (%2)", name _patient, _why];};
};

switch (_mode) do {
    case "request": {
        _args params [["_stand", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_attach", true, [true]],
            ["_requester", objNull, [objNull]], ["_part", "", [""]]];
        private _say = {
            if (!isNull _requester) then {["ACME_ivStandMessage", [_this], _requester] call CBA_fnc_targetEvent;};
            if (call ACME_fnc_debugEnabled) then {diag_log text format ["[ACME] IV stand request: %1", _this];};
        };
        if (isNull _stand || {isNull _patient}) exitWith {};
        _part = toLowerANSI _part;
        if (!_attach) exitWith {
            private _i = ACME_ivStand_hung findIf {(_x select 0) isEqualTo _stand && {(_x select 2) isEqualTo _patient} && {_part == "" || {(_x select 4) == _part}}};
            if (_i < 0) exitWith {};
            (ACME_ivStand_hung select _i) params ["", "_slot", "", "_jip"];
            [_stand, _slot, _patient, "", _jip] call _fnc_clear;
            "Bag taken down from the IV stand." call _say;
        };
        if !(missionNamespace getVariable ["ACME_sys_hang", true]) exitWith {};
        if (!alive _patient) exitWith {};
        if (_part == "") then {
            // the first running limb not already hung
            {
                if (_part == "" && {!(toLowerANSI _x in (_patient getVariable ["ACME_hang_StandParts", []]))} && {[_patient, _x] call ACME_fnc_ivStandFlowing}) then {_part = toLowerANSI _x;};
            } forEach keys (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
        };
        if (_part == "") exitWith {"No running IV bag to hang." call _say;};
        if ((ACME_ivStand_hung findIf {(_x select 2) isEqualTo _patient && {(_x select 4) == _part}}) >= 0) exitWith {"That bag is already on an IV stand." call _say;};
        if ((_stand distance _patient) > _leash) exitWith {"The line doesn't reach that stand." call _say;};
        if !([_patient, _part] call ACME_fnc_ivStandFlowing) exitWith {"No running IV bag to hang." call _say;};
        private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
        if (!isNull _holder && {_holder isNotEqualTo _requester} && {alive _holder} && {_holder getVariable ["ACME_hang_Active", false]}) exitWith {
            "Someone is holding that bag up." call _say;
        };
        private _slots = _stand getVariable ["ACME_ivStand_slots", [objNull, objNull]];
        private _slot = _slots findIf {isNull _x};
        if (_slot < 0) exitWith {"Both hooks on this stand are in use." call _say;};

        // the bag art: that limb's running bag, its fluid and size, as for a bag held up by hand
        private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
        private _volume = (_bags param [(_bags findIf {(_x param [1, 0]) > 0.5}) max 0, []]) param [1, 500];
        private _fluid = [_patient, _part] call ACME_fnc_hangBagFluidType;
        private _vol = if (_volume <= 375) then {250} else {if (_volume <= 750) then {500} else {1000}};
        private _modelClass = switch (_vol) do {case 250: {"ACME_IVBagObject_250"}; case 1000: {"ACME_IVBagObject_1000"}; default {"ACME_IVBagObject"};};
        private _tex = if (_fluid == "plasmalyte") then {format ["\acm_extended\data\iv_bag\IVBag_plasmalyte_%1ml_ca.paa", _vol]} else {
            format ["\z\ace\addons\medical_treatment\data\IVBag_%1_%2ml_ca.paa", switch (_fluid) do {case "blood": {"blood"}; case "plasma": {"plasma"}; default {"saline"};}, _vol]};
        private _ropeClass = switch (_fluid) do {
            case "blood": {"ACME_IVLine_Rope_Blood"};
            case "plasma": {"ACME_IVLine_Rope_Plasma"};
            default {missionNamespace getVariable ["ACME_hang_ropeClass", "ACME_IVLine_Rope"]};
        };

        _slots = +_slots;
        _slots set [_slot, _patient];
        _stand setVariable ["ACME_ivStand_slots", _slots, true];
        private _parts = +(_stand getVariable ["ACME_ivStand_parts", ["", ""]]);
        _parts set [_slot, _part];
        _stand setVariable ["ACME_ivStand_parts", _parts, true];
        if ((_stand getVariable ["ACME_ivStand_decor", []]) isEqualTo []) then {
            _stand setVariable ["ACME_ivStand_decor", _sources apply {_stand animationSourcePhase _x}];
        };
        _stand animateSource [_sources select _slot, 1, true];
        ACME_ivStand_counter = (missionNamespace getVariable ["ACME_ivStand_counter", 0]) + 1;
        private _jip = format ["ACME_ivStand_%1", ACME_ivStand_counter];
        ACME_ivStand_hung pushBack [_stand, _slot, _patient, _jip, _part];
        [_patient] call _fnc_patientState;
        ["ACME_ivStandVisual", [_stand, _slot, _patient, true, _jip, _modelClass, _tex, _ropeClass, _vol, _part], _jip] call CBA_fnc_globalEventJIP;
        "Bag hung on the IV stand." call _say;
        if (!isNull _requester) then {
            [_patient, "activity", "%1 hung an IV bag on a stand", [[_requester, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
        };
    };
    case "watch": {
        {
            _x params ["_stand", "_slot", "_patient", "_jip", ["_part", ""]];
            private _why = switch (true) do {
                case (isNull _stand): {"stand gone"};
                case (isNull _patient || {!alive _patient}): {"casualty died"};
                case (!(missionNamespace getVariable ["ACME_sys_hang", true])): {"hang bag turned off"};
                case (!isNull objectParent _patient): {"casualty in a vehicle"};
                case ((_stand distance _patient) > _leash + 0.25): {"out of the line's reach"};
                case (!([_patient, _part] call ACME_fnc_ivStandFlowing)): {"bag ran dry"};
                default {""};
            };
            if (_why != "") then {
                [_stand, _slot, _patient, _why, _jip] call _fnc_clear;
                if (_why == "out of the line's reach") then {
                    {["ACME_ivStandMessage", ["The IV line pulled free of the stand."], _x] call CBA_fnc_targetEvent;}
                        forEach (allPlayers select {_x distance _stand < 6 || {_x distance _patient < 6}});
                };
            } else {
                if ((_patient getVariable ["ACME_hang_flowMult", 1]) != _boost) then {_patient setVariable ["ACME_hang_flowMult", _boost, true];};
            };
        } forEach +ACME_ivStand_hung;
    };
};
