// the source list selection. _this, from onLBSelChanged, is [_ctrl, _index], and the lbdata holds the source key.
params ["_ctrl", "_index"];
// ignore selection events fired by our own programmatic lbSetCurSel during the dialog setup.
if (uiNamespace getVariable ["ACME_SK_Suppress", false]) exitWith {};
private _key = _ctrl lbData _index;
if (_key == "") exitWith {};
private _player = ACE_player;

switch (_key) do {
    // a saline flush is a 10 ml prefilled barrel, so force size 10 and load it full, with the plunger all the way up.
    case "Saline": {
        if (([_player, "ACM_SalineFlush_10"] call ACME_fnc_itemCount) < 1) exitWith {
            ["No prefilled saline flush (ACM_SalineFlush_10) in your kit."] call ACME_fnc_syringeKitInfo;
            lbSetCurSel [_ctrl, -1];
        };
        uiNamespace setVariable ["ACME_SK_Size", 10];
        uiNamespace setVariable ["ACME_SK_Source", "Saline"];
        uiNamespace setVariable ["ACME_SK_Vol", 10];  // full
        uiNamespace setVariable ["ACME_SK_SalineBase", -1];  // not yet wasted/locked
        uiNamespace setVariable ["ACME_SK_EpiMl", 0];
        uiNamespace setVariable ["ACME_SK_Med", ""];
        uiNamespace setVariable ["ACME_SK_Grab", false];
        ["10 mL flush loaded. Push plunger DOWN to your volume, then Waste."] call ACME_fnc_syringeKitInfo;
    };

    // epinephrine must have been wasted to a saline base first. it enters draggable draw mode: pull up to draw however
    // much epi you want, floored at the saline base.
    case "EpinephrineCardiac": {
        if ((uiNamespace getVariable ["ACME_SK_Source", ""]) != "Saline") exitWith {
            ["Load a Saline Flush base first."] call ACME_fnc_syringeKitInfo;
            lbSetCurSel [_ctrl, -1];
        };
        private _base = uiNamespace getVariable ["ACME_SK_SalineBase", -1];
        if (_base < 0) exitWith {
            ["Waste down to your saline volume and press Waste first, then draw epi."] call ACME_fnc_syringeKitInfo;
            lbSetCurSel [_ctrl, -1];
        };
        if (([_player, "EpinephrineCardiac"] call ACME_fnc_infusionVialVolume) < 1) exitWith {
            ["No epinephrine vial (ACME_Vial_EpinephrineCardiac) in your kit."] call ACME_fnc_syringeKitInfo;
            lbSetCurSel [_ctrl, -1];
        };
        private _size = uiNamespace getVariable ["ACME_SK_Size", 10];
        if (_base >= _size) exitWith {
            ["Syringe is full of saline. Waste some first."] call ACME_fnc_syringeKitInfo;
            lbSetCurSel [_ctrl, -1];
        };
        uiNamespace setVariable ["ACME_SK_Med", "EpinephrineCardiac"];
        uiNamespace setVariable ["ACME_SK_EpiMl", 0];
        uiNamespace setVariable ["ACME_SK_Vol", _base];  // start at the floor
        uiNamespace setVariable ["ACME_SK_Grab", false];
        [format ["Epi selected. Grab the plunger and pull UP to draw epi on top of %1 mL saline.", (_base toFixed 1)]] call ACME_fnc_syringeKitInfo;
    };
};

call ACME_fnc_syringeKitRender;
