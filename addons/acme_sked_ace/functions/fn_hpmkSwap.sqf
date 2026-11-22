/*
 * Where the casualty is local: swap the HPMK-I shell between the normal and the squeezed (in SKED) model,
 * keeping what is in its pockets. Dead casualties too, so a body taken out of the SKED gets the normal
 * shell back. Does nothing without acme_hpmk, or if the casualty is not wearing it.
 * Arguments: 0: casualty, 1: to the squeezed model <BOOL>.
 */
params ["_unit", "_toSked"];
if (!local _unit) exitWith {};
if (!isClass (configFile >> "CfgWeapons" >> "ACME_HPMK_Worn_Sked")) exitWith {};
private _lo = getUnitLoadout _unit;
private _vest = _lo select 4;
if (_vest isEqualTo []) exitWith {};
// (closed or with the chest opened: each has its model for the SKED)
private _open = (_vest select 0) in ["ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"];
private _plain = ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Open"] select _open;
private _from = [_plain + "_Sked", _plain] select _toSked;
private _to = [_plain, _plain + "_Sked"] select _toSked;
if !((_vest select 0) isEqualTo _from) exitWith {};
if !(isClass (configFile >> "CfgWeapons" >> _to)) exitWith {};
_lo set [4, [_to, _vest select 1]];
_unit setUnitLoadout [_lo, false];
