/*
 * Where the casualty is local: make what he wears agree with his HPMK state (ACME_hpmk_state).
 * Wrapped or exposed, he wears the shell, which is a vest: ACME_HPMK_Worn closed, ACME_HPMK_Worn_Open with chest
 * and left arm uncovered. A living casualty is undressed for it as a litter undresses him (acme_sked_fnc_gearHide:
 * everything he wears and carries is kept as one loadout, on him and on the server), so the shell lies on him and
 * not round a plate carrier and elbow pads. He gets it all back when the shell comes off, unless he is on a litter
 * then: the litter gives it back when he is unstrapped (and does not while he is still wrapped).
 * Where he cannot be undressed (the setting acme_sked_strip is off, or he is dead: a body is dressed piece by
 * piece), the shell takes the place of his own vest; what was in that vest goes into the shell's
 * pockets. His vest, helmet and night vision are remembered (ACME_hpmk_stowed) and put
 * back, with what is in the pockets then, when the shell comes off.
 * He is also held in the pose the shell is made for (ACME_fnc_hpmkPose).
 * Arguments: 0: casualty. Returns: nothing.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};
if !(isClass (configFile >> "CfgWeapons" >> "ACME_HPMK_Worn")) exitWith {};
private _shells = ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"];
private _want = switch (_patient getVariable ["ACME_hpmk_state", ""]) do {
    case "wrapped": {"ACME_HPMK_Worn"};
    case "exposed": {["ACME_HPMK_Worn", "ACME_HPMK_Worn_Open"] select (isClass (configFile >> "CfgWeapons" >> "ACME_HPMK_Worn_Open"))};
    default {""};
};
// (in a SKED the shell, closed or opened, is the one that is held inside the SKED, as acme_sked_fnc_hpmkSwap has it)
if (_want != "" && {(typeOf (_patient getVariable ["acme_sked_litter", objNull])) == "ACME_SKED_Wrapped"}
    && {missionNamespace getVariable ["acme_sked_hpmkSqueeze", true]}
    && {isClass (configFile >> "CfgWeapons" >> (_want + "_Sked"))}) then {_want = _want + "_Sked";};
private _has = vest _patient;
private _same = if (_want == "") then {!(_has in _shells)} else {
    _has == _want || {_has == (_want + "_Sked")}
};
if (_same) exitWith {[_patient] call ACME_fnc_hpmkPose;};

private _stowed = _patient getVariable ["ACME_hpmk_stowed", []];
_stowed params [["_vestWas", ""], ["_helmetWas", ""], ["_nvgWas", ""]];
private _beside = [];
private _dressAgain = false;
if (alive _patient) then {
    if (_want != "" && {!isNil "acme_sked_fnc_gearHide"}) then {
        [_patient, objNull] call acme_sked_fnc_gearHide;
        _has = vest _patient;
    };
    private _lo = getUnitLoadout _patient;
    private _vest = _lo select 4;
    private _items = if (_vest isEqualTo []) then {[]} else {+(_vest select 1)};
    if (_want != "") then {
        if !(_has in _shells) then {
            // the shell goes on: remember what it takes the place of
            _patient setVariable ["ACME_hpmk_stowed", [_has, _lo select 6, (_lo select 9) param [5, ""]], true];
            _lo set [6, ""];
            (_lo select 9) set [5, ""];
        };
        _lo set [4, [_want, _items]];
    } else {
        private _kept = _patient getVariable ["acme_sked_gear", []];
        if (_kept isEqualTo []) then {
            if (_vestWas != "") then {_lo set [4, [_vestWas, _items]];} else {
                _lo set [4, []];
                if (_items isNotEqualTo []) then {_beside = _items;};
            };
            if ((_lo select 6) == "") then {_lo set [6, _helmetWas];};
            if (((_lo select 9) param [5, ""]) == "") then {(_lo select 9) set [5, _nvgWas];};
        } else {
            // a litter has undressed him and keeps his loadout: it goes there
            private _saved = _kept select 0;
            private _savedVest = _saved select 4;
            if (_savedVest isEqualTo [] || {(_savedVest select 0) in _shells}) then {
                if (_vestWas != "") then {_saved set [4, [_vestWas, _items]];} else {
                    _saved set [4, []];
                    if (_items isNotEqualTo []) then {_beside = _items;};
                };
            } else {
                (_savedVest select 1) append _items;
            };
            if ((_saved select 6) == "") then {_saved set [6, _helmetWas];};
            if (((_saved select 9) param [5, ""]) == "") then {(_saved select 9) set [5, _nvgWas];};
            _patient setVariable ["acme_sked_gear", _kept, true];
            ["acme_sked_gearKeep", [_patient, _kept]] call CBA_fnc_serverEvent;
            _lo set [4, []];
            _dressAgain = isNull (_patient getVariable ["acme_sked_litter", objNull])
                && {isNull (_patient getVariable ["acme_sked_placing", objNull])};
        };
        _patient setVariable ["ACME_hpmk_stowed", nil, true];
    };
    _patient setUnitLoadout [_lo, false];
    // no litter holds him: the shell is off, and he gets back what was taken off him for it
    if (_dressAgain && {!isNil "acme_sked_fnc_gearShow"}) then {[_patient] call acme_sked_fnc_gearShow;};
} else {
    // A dead casualty takes no loadout, and nothing can be put into his pockets through him: he is undressed and
    // dressed piece by piece, and pockets are filled through their own containers. He is undressed for the shell
    // as a living casualty is (the whole loadout kept in acme_sked_gear, on him and on the server), and dressed
    // again when the shell comes off, on a litter or not: a litter leaves a body dressed.
    private _fill = {
        params ["_box", "_things"];
        if (isNull _box) exitWith {false};
        {
            // one line of a container: [class, count], [magazine, count, rounds] or [[weapon and its parts], count]
            _x params ["_what", ["_count", 1], ["_rounds", -1]];
            if (_what isEqualType []) then {_box addWeaponWithAttachmentsCargoGlobal [_what, _count];} else {
                if (_what != "") then {
                    if (_rounds >= 0) then {_box addMagazineAmmoCargo [_what, _count, _rounds];} else {
                        if (isClass (configFile >> "CfgVehicles" >> _what)) then {_box addBackpackCargoGlobal [_what, _count];}
                        else {_box addItemCargoGlobal [_what, _count];};
                    };
                };
            };
        } forEach _things;
        true
    };
    private _vest = (getUnitLoadout _patient) param [4, []];
    private _items = if (_vest isEqualTo []) then {(vestItems _patient) apply {[_x, 1]}} else {+(_vest select 1)};
    private _kept = _patient getVariable ["acme_sked_gear", []];
    if (_want != "") then {
        if (_has in _shells) then {
            // one shell for another: what is in its pockets goes along
            removeVest _patient;
            _patient addVest _want;
            if !([vestContainer _patient, _items] call _fill) then {_beside = _items;};
        } else {
            if (missionNamespace getVariable ["acme_sked_strip", true]) then {
                if (_kept isEqualTo []) then {
                    _kept = [getUnitLoadout _patient, [], ""];
                    _patient setVariable ["acme_sked_gear", _kept, true];
                    ["acme_sked_gearKeep", [_patient, _kept]] call CBA_fnc_serverEvent;
                };
                removeAllWeapons _patient;
                removeUniform _patient;
                removeVest _patient;
                removeBackpackGlobal _patient;
                removeHeadgear _patient;
                removeGoggles _patient;
                {_patient unlinkItem _x;} forEach (assignedItems _patient);
                _patient addVest _want;
            } else {
                // not undressed (the setting): the shell takes the place of his vest, helmet and night vision
                _patient setVariable ["ACME_hpmk_stowed", [_has, headgear _patient, hmd _patient], true];
                removeHeadgear _patient;
                if ((hmd _patient) != "") then {_patient unlinkItem (hmd _patient);};
                removeVest _patient;
                _patient addVest _want;
                if !([vestContainer _patient, _items] call _fill) then {_beside = _items;};
            };
        };
    } else {
        removeVest _patient;
        if (_kept isNotEqualTo []) then {
            (_kept select 0) params ["_w0", "_w1", "_w2", "_uniWas", "_ownVest", "_packWas", ["_helmet", ""], ["_glasses", ""], "_w8", ["_linked", []]];
            _uniWas params [["_uni", ""], ["_uniItems", []]];
            _ownVest params [["_vestClass", ""], ["_vestItems", []]];
            _packWas params [["_pack", ""], ["_packItems", []]];
            private _left = [[], [], [], [], [], [], "", "", [], ["", "", "", "", "", ""]];
            if (_uni != "" && {(uniform _patient) == ""}) then {
                _patient forceAddUniform _uni;
                if ((uniform _patient) != _uni || {!([uniformContainer _patient, _uniItems] call _fill)}) then {_left set [3, _uniWas];};
            };
            if (_vestClass != "" && {!(_vestClass in _shells)}) then {
                _patient addVest _vestClass;
                if ((vest _patient) != _vestClass || {!([vestContainer _patient, _vestItems + _items] call _fill)}) then {
                    _left set [4, [_vestClass, _vestItems + _items]];
                };
            } else {
                if (_items isNotEqualTo []) then {_beside = _items;};
            };
            if (_pack != "" && {(backpack _patient) == ""}) then {
                _patient addBackpackGlobal _pack;
                clearAllItemsFromBackpack _patient;
                if ((backpack _patient) != _pack || {!([backpackContainer _patient, _packItems] call _fill)}) then {_left set [5, _packWas];};
            };
            if (_helmet != "" && {(headgear _patient) == ""}) then {
                _patient addHeadgear _helmet;
                if ((headgear _patient) != _helmet) then {_left set [6, _helmet];};
            };
            if (_glasses != "" && {(goggles _patient) == ""}) then {
                _patient addGoggles _glasses;
                if ((goggles _patient) != _glasses) then {_left set [7, _glasses];};
            };
            {
                if (_x != "") then {
                    _patient linkItem _x;
                    if !(_x in (assignedItems _patient)) then {(_left select 9) set [_forEachIndex, _x];};
                };
            } forEach _linked;
            // a body holds no weapon: what he had in hand when he was undressed is laid beside him, with whatever
            // did not go back on
            {if (!isNil "_x" && {_x isEqualType []} && {_x isNotEqualTo []}) then {_left set [_forEachIndex, _x];};} forEach [_w0, _w1, _w2];
            if (!isNil "_w8" && {_w8 isEqualType []} && {_w8 isNotEqualTo []}) then {_left set [8, _w8];};
            if (_left isNotEqualTo [[], [], [], [], [], [], "", "", [], ["", "", "", "", "", ""]] && {!isNil "acme_sked_fnc_gearDrop"}) then {
                [_patient, _left] call acme_sked_fnc_gearDrop;
            };
            _patient setVariable ["acme_sked_gear", nil, true];
            ["acme_sked_gearGone", [_patient]] call CBA_fnc_serverEvent;
        } else {
            if (_vestWas != "") then {_patient addVest _vestWas;};
            if ((headgear _patient) == "" && {_helmetWas != ""}) then {_patient addHeadgear _helmetWas;};
            if ((hmd _patient) == "" && {_nvgWas != ""}) then {_patient linkItem _nvgWas;};
            if !([vestContainer _patient, _items] call _fill) then {_beside = _items;};
        };
        _patient setVariable ["ACME_hpmk_stowed", nil, true];
    };
};
if (_beside isNotEqualTo []) then {
    // there was no vest of his own for what is in the shell's pockets: it is laid beside him
    if (isNil "acme_sked_fnc_gearDrop") then {
        private _pile = createVehicle ["GroundWeaponHolder", (getPosATL _patient) vectorAdd [0.6, 0, 0], [], 0, "CAN_COLLIDE"];
        {
            _x params ["_what", ["_count", 1]];
            if (_what isEqualType "") then {_pile addItemCargoGlobal [_what, _count];};
        } forEach _beside;
    } else {
        [_patient, [[], [], [], [], ["", _beside], [], "", "", [], ["", "", "", "", "", ""]]] call acme_sked_fnc_gearDrop;
    };
};
[_patient] call ACME_fnc_hpmkPose;
