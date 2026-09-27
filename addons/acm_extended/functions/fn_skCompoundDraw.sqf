// "Draw" in the compound flow. the plunger is at the floor plus the volume of this drug.
// lock the drug in as a component, advance the floor to the new fill so the next drug draws on top, record the vial
// to consume on save, and leave the syringe open for the next component.
// it requires a selected medication and a positive volume, the vial in inventory, and room left in the barrel.
// call ACME_fnc_skCompoundDraw.
disableSerialization;
private _dlg = findDisplay 84000;
if (isNull _dlg) exitWith {};
if ((uiNamespace getVariable ["ACME_SK_WasteStage", ""]) != "compound") exitWith {};

private _cap    = uiNamespace getVariable ["ACME_SK_WasteCap", 10];
private _floor  = uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0];
private _fill   = ((uiNamespace getVariable ["ACME_SK_WasteFill", ACM_circulation_SyringeDraw_DrawnAmount]) max _floor) min _cap;
private _drugMl = _fill - _floor;

private _med = ACM_circulation_SyringeDraw_Medication;
if (isNil "_med" || {_med isEqualTo ""}) exitWith {
    ["Select a medication, then draw.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _locked = uiNamespace getVariable ["ACME_SK_CompoundComponents", []];
if (_drugMl <= 0.05) exitWith {
    ["Grab the plunger and pull down to draw some drug first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _vial = [_med] call ACME_fnc_vialClass;
private _required = _drugMl;
{if ((_x select 0) == _med) then {_required = _required + (_x select 1);};} forEach _locked;
private _holder = [ACE_player] call ACME_fnc_vialHolder;
if (([_holder, _med] call ACME_fnc_infusionVialVolume) + 0.000001 < _required) exitWith {
    [format ["No %1 vial in inventory.", _med], 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// lock this component in, advance the floor to the current fill, and remember the vial to remove on save.
private _components = uiNamespace getVariable ["ACME_SK_CompoundComponents", []];
_components pushBack [_med, _drugMl];
uiNamespace setVariable ["ACME_SK_CompoundComponents", _components];

private _vials = uiNamespace getVariable ["ACME_SK_CompoundVials", []];
_vials pushBack _vial;
uiNamespace setVariable ["ACME_SK_CompoundVials", _vials];

uiNamespace setVariable ["ACME_SK_WasteFloorMl", _fill];
uiNamespace setVariable ["ACME_SK_WasteMoving", false];  // release the grab so the next pull is deliberate

// re-enable the drug menu so the next drug can be picked. the own per-frame loop of ACM disables it once drawnamount
// is above 0, so force it back on for the compound flow.
private _medList = _dlg displayCtrl 84006;
if (!isNull _medList) then { _medList ctrlEnable true; };
private _medListBtn = _dlg displayCtrl 84007;
if (!isNull _medListBtn) then { _medListBtn ctrlEnable true; };

// B73 tactile draw acknowledgement. Count successful locked pulls, not unique medications.
private _drawCount = count _components;
uiNamespace setVariable ["ACME_SK_CompoundDrawCount", _drawCount];
private _drawBtn = _dlg displayCtrl 84003;
if (!isNull _drawBtn) then {
    private _gen = (_dlg getVariable ["ACME_SK_DrawFeedbackGen", 0]) + 1;
    _dlg setVariable ["ACME_SK_DrawFeedbackGen", _gen];
    _drawBtn ctrlSetText format ["Drawn! (%1)",_drawCount];
    _drawBtn ctrlSetBackgroundColor (["success",0.88] call ACME_fnc_a11yColor);
    _drawBtn ctrlCommit 0;
    [{
        params ["_oldDisplay","_expectedGen","_count"];
        private _live = findDisplay 84000;
        if (isNull _live || {!(_live isEqualTo _oldDisplay)} || {(_live getVariable ["ACME_SK_DrawFeedbackGen",0]) != _expectedGen}
            || {(uiNamespace getVariable ["ACME_SK_WasteStage",""]) != "compound"}) exitWith {};
        private _b = _live displayCtrl 84003;
        if (!isNull _b) then {
            _b ctrlSetText format ["Draw (%1)",_count];
            _b ctrlSetBackgroundColor [0.05,0.05,0.05,0.65];
            _b ctrlCommit 0;
        };
    },[_dlg,_gen,_drawCount],1.00] call CBA_fnc_waitAndExecute;
};
