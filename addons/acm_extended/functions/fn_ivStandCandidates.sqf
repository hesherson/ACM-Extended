/* B395: what an IV stand's menu offers (fn_ivStandInit.sqf).
 * _mode "hang": each running IV bag (casualty and limb) within the line's reach of the stand that is not already on
 *               a stand and whose bag nobody else is holding up, while the stand has a free hook.
 * _mode "down": the bags hung on this stand.
 * Returns [[casualty, label, id, limb], ...]. */
params [["_stand", objNull, [objNull]], ["_player", objNull, [objNull]], ["_mode", "hang", [""]]];
if (isNull _stand) exitWith {[]};
private _slots = _stand getVariable ["ACME_ivStand_slots", [objNull, objNull]];
private _parts = _stand getVariable ["ACME_ivStand_parts", ["", ""]];
private _limbs = createHashMapFromArray [["leftarm", "left arm"], ["rightarm", "right arm"], ["leftleg", "left leg"],
    ["rightleg", "right leg"], ["body", "chest"], ["head", "head"]];
private _fluidLabel = {
    switch (_this) do {case "blood": {"blood"}; case "plasma": {"plasma"}; case "plasmalyte": {"Plasma-Lyte"}; default {"fluids"};}
};
if (_mode == "down") exitWith {
    private _out = [];
    {
        if (!isNull _x) then {
            private _part = _parts param [_forEachIndex, ""];
            private _fluid = [_x, _part] call ACME_fnc_hangBagFluidType;
            _out pushBack [_x, format ["%1, %2 (%3)", [_x, false, true] call ace_common_fnc_getName, _limbs getOrDefault [_part, _part],
                _fluid call _fluidLabel], str _forEachIndex, _part];
        };
    } forEach _slots;
    _out
};
private _stagedNow = _stand getVariable ["ACME_ivStand_staged", [[], []]];
if (([0, 1] findIf {isNull (_slots select _x) && {(_stagedNow select _x) isEqualTo []}}) < 0) exitWith {[]};
private _leash = missionNamespace getVariable ["ACME_hang_leash", 3];
private _out = [];
{
    private _patient = _x;
    private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
    private _heldByOther = !isNull _holder && {_holder isNotEqualTo _player} && {alive _holder} && {_holder getVariable ["ACME_hang_Active", false]};
    if (_patient isNotEqualTo _player && {alive _patient} && {isNull objectParent _patient} && {!_heldByOther}) then {
        private _hung = _patient getVariable ["ACME_hang_StandParts", []];
        private _mine = (_player getVariable ["ACME_hang_Active", false]) && {(_player getVariable ["ACME_hang_Patient", objNull]) isEqualTo _patient};
        {
            private _part = toLowerANSI _x;
            if (!(_part in _hung) && {[_patient, _part] call ACME_fnc_ivStandFlowing}) then {
                private _fluid = [_patient, _part] call ACME_fnc_hangBagFluidType;
                private _held = _mine && {(toLowerANSI (_player getVariable ["ACME_hang_Part", ""])) in ["", _part]};
                _out pushBack [_patient, format [["%1, %2 (%3)", "%1, %2 (%3, the bag you hold)"] select _held,
                    [_patient, false, true] call ace_common_fnc_getName, _limbs getOrDefault [_part, _part], _fluid call _fluidLabel],
                    format ["%1_%2", _forEachIndex, _part], _part];
            };
        } forEach keys (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
    };
} forEach (_stand nearEntities ["CAManBase", _leash]);
_out
