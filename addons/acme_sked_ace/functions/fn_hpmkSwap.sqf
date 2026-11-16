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
private _from = ["ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn"] select _toSked;
private _to = ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked"] select _toSked;
if !((_vest select 0) isEqualTo _from) exitWith {};
_lo set [4, [_to, _vest select 1]];
_unit setUnitLoadout [_lo, false];
