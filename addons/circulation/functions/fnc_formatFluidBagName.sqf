#include "..\script_component.hpp"
/*
 * Author: Blue / ACM Extended Fork
 * Get config entry for fluid bags.
 *
 * Extended bags whose runtime fluid type is not represented by a stock ACE inventory classname are resolved here
 * to their real inventory items. The no-prefix path remains the ACE medical-treatment IV data key used by logs.
 *
 * Arguments:
 * 0: Type <STRING>
 * 1: Fluid Bag Volume <NUMBER>
 * 2: Blood Type <NUMBER>
 * 3: Don't add prefix <BOOL>
 *
 * Return Value:
 * Formatted name <STRING>
 */

params ["_type", "_targetVolume", ["_bloodType", -1], ["_noPrefix", false]];

private _typeLower = toLowerANSI _type;

// ACME-owned fluid carriers use their own inventory classnames. Without this mapping ACM constructs classes such
// as ACE_plasmalyteIV_500, which do not exist as inventory items. That made a hung Plasma-Lyte bag render as an
// empty row and also made generic detach/return paths resolve the wrong class.
private _extendedInventoryClass = switch (true) do {
    case (_typeLower == "acme_propofol"): {"ACM_Vial_Propofol"};
    case (_typeLower == "plasmalyte" && {_targetVolume >= 1000}): {"ACME_PlasmaLyteBag"};
    case (_typeLower == "plasmalyte" && {_targetVolume == 500}): {"ACME_PlasmaLyteBag_500"};
    case (_typeLower == "plasmalyte" && {_targetVolume == 250}): {"ACME_PlasmaLyteBag_250"};
    case (_typeLower == "plasmalyte" && {_targetVolume == 100}): {"ACME_PlasmaLyteBag_100"};
    case (_typeLower == "esmolol" && {_targetVolume == 250}): {"ACM_EsmololBag"};
    case (_typeLower == "hts" && {_targetVolume == 250}): {"ACME_HTSBag"};
    case (_typeLower == "magnesium" && {_targetVolume == 50}): {"ACME_MagnesiumBag"};
    case (_typeLower == "mannitol" && {_targetVolume == 500}): {"ACME_MannitolBag"};
    case (_typeLower == "saline" && {_targetVolume == 50}): {"ACME_SalineBag_50"};
    case (_typeLower == "saline" && {_targetVolume == 100}): {"ACME_SalineBag_100"};
    default {""};
};

if (_extendedInventoryClass != "" && {!_noPrefix}) exitWith {_extendedInventoryClass};

// The no-prefix form is not an inventory classname. It is the ace_medical_treatment >> IV data entry consumed by
// getFluidBagString and the treatment system. ACME's custom IV data keys retain their authored casing and, unlike
// stock ACE 1000 mL bags, Plasma-Lyte explicitly uses the _1000 suffix.
if (_noPrefix) then {
    private _extendedDataClass = switch (true) do {
        case (_typeLower == "acme_propofol"): {"ACME_PropofolIV_50"};
        case (_typeLower == "plasmalyte" && {_targetVolume in [100,250,500,1000]}): {format ["PlasmaLyteIV_%1", _targetVolume]};
        case (_typeLower == "esmolol" && {_targetVolume == 250}): {"EsmololIV_250"};
        case (_typeLower == "hts" && {_targetVolume == 250}): {"HTSIV_250"};
        case (_typeLower == "magnesium" && {_targetVolume == 50}): {"MagnesiumIV_50"};
        case (_typeLower == "mannitol" && {_targetVolume == 500}): {"MannitolIV_500"};
        case (_typeLower == "saline" && {_targetVolume in [50,100]}): {format ["SalineIV_%1", _targetVolume]};
        default {""};
    };
    if (_extendedDataClass != "") exitWith {_extendedDataClass};
};

[([true, _type, _targetVolume, -1, _noPrefix] call FUNC(getFluidBagConfigName)), ([false, _type, _targetVolume, _bloodType, _noPrefix] call FUNC(getFluidBagConfigName))] select (_type in ["Blood","FreshBlood","FBTK"])
