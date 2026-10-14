/* Legacy bench retains exact recipe validation and writes the same B12 syringe as the Narc Box. */
private _player = uiNamespace getVariable ["ACME_SK_BenchMedic", objNull];
if (isNull _player || {_player isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
private _med = uiNamespace getVariable ["ACME_SK_Med", ""];
private _epi = uiNamespace getVariable ["ACME_SK_EpiMl", 0];
private _base = uiNamespace getVariable ["ACME_SK_SalineBase", -1];
private _size = uiNamespace getVariable ["ACME_SK_Size", 10];
if (!([_med, _size, _epi, _base] call ACME_fnc_epinephrineRecipe)) exitWith {
    ["Use a 10 mL flush, waste 1 mL, then draw 1 mL of epinephrine 1:10,000. Final 10 mcg/mL; 100 mcg total."] call ACME_fnc_syringeKitInfo;
};
if !([_player] call ACME_fnc_epinephrinePrepare) exitWith {["Missing the flush or 1:10,000 epinephrine."] call ACME_fnc_syringeKitInfo;};
// reset the bench for the next syringe first, before any logging or messaging, so the plunger always returns to
// empty even if a downstream call throws.
// clear the state and hard-snap the plunger bar and fluid column to the empty, needle, position directly, rather
// than relying solely on the render pass.
uiNamespace setVariable ["ACME_SK_Vol", 0];
uiNamespace setVariable ["ACME_SK_SalineBase", -1];
uiNamespace setVariable ["ACME_SK_EpiMl", 0];
uiNamespace setVariable ["ACME_SK_Med", ""];
uiNamespace setVariable ["ACME_SK_Source", ""];
uiNamespace setVariable ["ACME_SK_Grab", false];
private _display = uiNamespace getVariable ["ACME_SK_DLG", displayNull];
if (!isNull _display) then {
    (_display displayCtrl 86318) lbSetCurSel -1;
    private _geo = uiNamespace getVariable ["ACME_SK_Geo", []];
    if !(_geo isEqualTo []) then {
        _geo params ["_gx", "_gyTop", "_gw", "_gh"];
        private _plH = _gh * 0.03;
        private _plunger = _display displayCtrl 86314;  // plunger stopper bar -> snap to the bottom (needle)
        if (!isNull _plunger) then { _plunger ctrlSetPosition [_gx - (_gw * 0.08), (_gyTop + _gh) - (_plH / 2), _gw * 1.16, _plH]; _plunger ctrlCommit 0; };
        private _fluid = _display displayCtrl 86313;  // fluid column -> empty + hidden
        if (!isNull _fluid) then { _fluid ctrlSetPosition [_gx, _gyTop + _gh, _gw, 0]; _fluid ctrlCommit 0; _fluid ctrlShow false; };
    };
};
call ACME_fnc_syringeKitRender;


["Stored in the Syringe Menu. Full syringe = 100 mcg; measured 1 mL = 10 mcg."] call ACME_fnc_syringeKitInfo;
