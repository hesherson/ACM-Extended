/*
 * Where the casualty is local: undress a casualty who has been strapped on a litter, or wrapped in the HPMK-I
 * (ACME_fnc_hpmkDress; then there is no litter). Everything they wear and
 * carry is taken off (uniform, vest, pack, helmet, glasses, night vision, weapons, radio, map and the rest),
 * so they lie under the blanket as a trauma casualty does. Nothing is thrown away. The whole loadout is kept:
 *   - on the casualty, in a public variable (acme_sked_gear), which a corpse keeps too;
 *   - on the server, in its own table (a second copy, handed back when they are unstrapped);
 *   - with CBA's extended loadout, so what other mods keep with a loadout (ACE earplugs and so on) comes back.
 * fn_gearShow.sqf gives it all back. An HPMK-I worn as a vest stays on. A dead casualty keeps their gear on:
 * a corpse cannot be dressed again reliably.
 * Arguments: 0: casualty, 1: litter (none: he is undressed for the HPMK-I, and no pack is laid on his legs).
 */
params ["_patient", ["_litter", objNull]];
if (!local _patient) exitWith {};
if (!(missionNamespace getVariable ["acme_sked_strip", true])) exitWith {};
private _kept = _patient getVariable ["acme_sked_gear", []];
if (_kept isEqualTo []) then {
    if (!alive _patient) exitWith {};
    private _saved = getUnitLoadout _patient;
    private _extended = if (isNil "CBA_fnc_getLoadout") then {[]} else {[_patient] call CBA_fnc_getLoadout};
    _kept = [_saved, _extended, name _patient];
    _patient setVariable ["acme_sked_gear", _kept, true];
    ["acme_sked_gearKeep", [_patient, _kept]] call CBA_fnc_serverEvent;
    private _bare = [[], [], [], [], [], [], "", "", [], ["", "", "", "", "", ""]];
    private _vest = _saved select 4;
    if (_vest isNotEqualTo [] && {(_vest select 0) in ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"]}) then {_bare set [4, _vest];};
    _patient setUnitLoadout [_bare, false];
    ["gear hidden", _litter, _patient, [(_saved select 3) param [0, ""], (_saved select 4) param [0, ""], (_saved select 5) param [0, ""]]] call acme_sked_fnc_traceTransport;
};
if (_kept isEqualTo [] || {isNull _litter}) exitWith {};

// Their pack lies on their legs for as long as they are on the litter (a picture of it: the real one is kept).
private _class = ((_kept select 0) select 5) param [0, ""];
if (_class == "" || {!isNull (_litter getVariable ["acme_sked_bag", objNull])}) exitWith {};
private _cfg = configFile >> "CfgVehicles" >> _class;
private _model = getText (_cfg >> "model");
private _place = getArray (configOf _litter >> "acmeLitterBag");
if (_model == "" || {count _place != 3}) exitWith {};
if ((_model select [0, 1]) == "\") then {_model = _model select [1];};
if ((toLowerANSI _model) select [count _model - 4] != ".p3d") then {_model = _model + ".p3d";};
private _bag = createSimpleObject [_model, getPosWorld _litter];
if (isNull _bag) exitWith {};
{_bag setObjectTextureGlobal [_forEachIndex, _x];} forEach (getArray (_cfg >> "hiddenSelectionsTextures"));
// Laid on its back panel, its top toward the casualty's head. In a pack's own axes the wearer is on the -Y side
// (measured in game), so -Y goes down and the shoulder straps end up under the pack, not in the air. It is put
// down by the middle of its own shape, not by its origin.
(0 boundingBoxReal _bag) params ["_min", "_max"];
private _mid = (_min vectorAdd _max) vectorMultiply 0.5;
private _depth = ((_max select 1) - (_min select 1)) / 2;
private _dir = [0, 0, 1];
private _up = [0, 1, 0];
private _side = _dir vectorCrossProduct _up;
private _turned = ((_side vectorMultiply (_mid select 0)) vectorAdd (_dir vectorMultiply (_mid select 1))) vectorAdd (_up vectorMultiply (_mid select 2));
_bag attachTo [_litter, (_place vectorAdd [0, 0, _depth]) vectorDiff _turned];
_bag setVectorDirAndUp [_dir, _up];
// (again a frame later: on an object attached in the same frame the first call does not always take)
[{
    params ["_bag", "_dir", "_up"];
    if (!isNull _bag) then {_bag setVectorDirAndUp [_dir, _up];};
}, [_bag, _dir, _up]] call CBA_fnc_execNextFrame;
_litter setVariable ["acme_sked_bag", _bag, true];
