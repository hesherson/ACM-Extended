disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
// this injects a syringe-size list and a flushes list onto the left of ACM's draw dialog, mirroring the drug, or
// medication, list that sits on the right. it is a runtime ctrlcreate onto the live display, so ACM's own
// controls are untouched. it is idempotent per dialog instance, because it is re-created fresh on each
// reopen.
private _display = findDisplay 84000;
if (isNull _display) exitWith {};
if (!isNull (_display displayCtrl 84130)) exitWith {};  // already injected on this instance.

// Return routing belongs to this display, even if a completion clears the global context.
private _ctx = missionNamespace getVariable ["ACME_infusion_pendingContext", []];
private _return = [];
if ((_ctx param [0, ""]) in ["active", "prepared"]) then {
    _return = [ACE_player, _ctx param [1, objNull], _ctx param [2, ""], _ctx param [13, true], _ctx param [14, -1]];
};
_display setVariable ["ACME_SK_Return", _return];
_display setVariable ["ACME_SK_ReturnPatient", uiNamespace getVariable ["ACME_SK_Patient", objNull]];
_display setVariable ["ACME_SK_PendingTagReady", false];
_display displayAddEventHandler ["Unload", {_this call ACME_fnc_skClose}];

// Mirror ACM's medication list onto the left, but do not inherit ACM's narrow 1/6.5 screen-width column.
// The visible medication rows carry medication + contents + vial-count columns, so the stock geometry clips names
// badly at larger UI scales. Keep the original inner edges fixed and grow both columns outward symmetrically.
private _listW = _uiW / 5.25;
private _columnInner = _uiW / 3.3;
private _leftX = (_uiX + (_uiW / 2) - _columnInner) - _listW;
private _rightX = _uiX + (_uiW / 2) + _columnInner;
private _nativeMedGeometry = _display displayCtrl 84006;
if (!isNull _nativeMedGeometry) then {
    private _mp = ctrlPosition _nativeMedGeometry;
    _nativeMedGeometry ctrlSetPosition [_rightX, _mp select 1, _listW, _mp select 3];
    _nativeMedGeometry ctrlCommit 0;
};
// The inventory target caption/button sits over the medication column. Give the caption the same usable width;
// the switch button keeps its compact native footprint.
private _medCaption = _display displayCtrl 84007;
if (!isNull _medCaption) then {
    private _cp = ctrlPosition _medCaption;
    _medCaption ctrlSetPosition [_rightX, _cp select 1, _listW, _cp select 3];
    _medCaption ctrlCommit 0;
};
private _topY  = safeZoneY + (safeZoneH / 2) - (safeZoneH / 5.3);
private _labelH = safeZoneH / 28;
private _sizeListH = safeZoneH / 5;
private _flushTopY = _topY + _sizeListH + (safeZoneH / 12);
private _flushListH = safeZoneH / 14;

// the syringe size: a label plus an ordered list of 1, 3, 5 and 10 ml.
private _sizeLabel = _display ctrlCreate ["ACME_SK_StyledLabel", 84129];
_sizeLabel ctrlSetPosition [_leftX, _topY - _labelH, _listW, _labelH];
_sizeLabel ctrlSetText "Syringe";
_sizeLabel ctrlCommit 0;

private _sizeList = _display ctrlCreate ["ACME_SK_StyledList", 84130];
_sizeList ctrlSetPosition [_leftX, _topY, _listW, _sizeListH];
_sizeList ctrlCommit 0;
lbClear _sizeList;
{
    private _i = _sizeList lbAdd format ["%1 mL Syringe", _x];
    _sizeList lbSetValue [_i, _x];
} forEach [1, 3, 5, 10];
_sizeList ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skPickSize}];

// flushes: a separate label and list under the sizes.
private _flushLabel = _display ctrlCreate ["ACME_SK_StyledLabel", 84131];
_flushLabel ctrlSetPosition [_leftX, _flushTopY - _labelH, _listW, _labelH];
_flushLabel ctrlSetText "Flushes";
_flushLabel ctrlCommit 0;

private _flushList = _display ctrlCreate ["ACME_SK_StyledList", 84132];
_flushList ctrlSetPosition [_leftX, _flushTopY, _listW, _flushListH];
_flushList ctrlCommit 0;
lbClear _flushList;
private _fi = _flushList lbAdd "Saline Flush (10 mL)";
_flushList lbSetData [_fi, "ACM_SalineFlush_10"];
_flushList ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skPickFlush}];

// B60: the old Drawn list stays retired. The persistent carousel now shares the center of the dialog with the
// Body Map and dynamically trades screen space with it instead of occupying this lower-left list footprint.
[ACE_player] call ACME_fnc_skStoreEnsureIds;

// B48: medications use ACM's native listbox again. Bind ACME's physical-vial session to that native
// selection rather than relying on the removed custom row-button overlay.
private _medListNative = _display displayCtrl 84006;
if (!isNull _medListNative) then {
    _medListNative ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skMedicationSelect;}];
    // B50: the native list is a backing selector only. Hide it before ACM can flash it over the custom rows.
    _medListNative ctrlShow false;
};

// Prepared syringe state was normalized above. Visible carousel/body controls are painted after they exist.

// Instantiate the merged ACE/ACM/Extended group, not a parallel device-icon list.
private _bodyGroup = _display ctrlCreate ["ace_medical_gui_BodyImage", 84140];
_bodyGroup ctrlShow false;
// B64 adaptive geometry.  The visible five-slot track stays narrower than the common IV/IO+IM / Draw toolbar on
// ultrawide displays, while syringe sprite size is now independent from that narrow track width (renderer-owned).
private _fillV = (missionNamespace getVariable ["ACME_SK_BodyFillV", 0.883]) max 0.05;
private _compactH = safeZoneH * 0.52 / _fillV;
private _expandedH = safeZoneH * 0.14 / _fillV;
private _compactW = _compactH * pixelW / pixelH;
private _expandedW = _expandedH * pixelW / pixelH;
private _compactRect = [_uiX + _uiW/2 - _compactW/2, safeZoneY + safeZoneH*0.035, _compactW, _compactH];
private _expandedRect = [_uiX + _uiW/2 - _expandedW/2, safeZoneY + safeZoneH*0.055, _expandedW, _expandedH];
private _carCenterX = _uiX + _uiW/2;
private _toolbarW = _uiW / 11;
// B68: compact navigation remains inside the route-row width. Promotion widens the carousel independently so tagged
// syringes have breathing room without making the resting Body Map look stretched on ultrawide.
private _carCompactW = _toolbarW * 0.78;
private _carExpandedW = (_toolbarW * 1.72) min (safeZoneH * 0.64);
private _drawRowY = safeZoneY + (safeZoneH / 1.08);
// Lift the whole carousel workspace. Even the enlarged promoted syringe/plunger must end above Draw Syringe.
// The plunger picture itself travels as much as ~25% of the syringe-control height below the barrel
// when full. Give compact and promoted states different bottoms so the *visible plunger*, not merely the
// barrel control, stays clear of Draw Syringe.
private _carCompactBottom = _drawRowY - safeZoneH*0.080;
private _carExpandedBottom = _drawRowY - safeZoneH*0.188;
private _carCompactH = safeZoneH*0.105;
private _carExpandedH = safeZoneH*0.380;
_display setVariable ["ACME_SK_BodyRectCompact", _compactRect];
_display setVariable ["ACME_SK_BodyRectExpanded", _expandedRect];
_display setVariable ["ACME_SK_CarouselRectCompact", [_carCenterX - _carCompactW/2, _carCompactBottom-_carCompactH, _carCompactW, _carCompactH]];
_display setVariable ["ACME_SK_CarouselRectExpanded", [_carCenterX - _carExpandedW/2, _carExpandedBottom-_carExpandedH, _carExpandedW, _carExpandedH]];
_display setVariable ["ACME_SK_CarouselRect", _display getVariable ["ACME_SK_CarouselRectCompact", []]];
private _rect = _compactRect;
_display setVariable ["ACME_SK_BodyRect", _rect];
_bodyGroup ctrlSetPosition _rect;
_bodyGroup ctrlCommit 0;
{
    if ((ctrlParentControlsGroup _x) isEqualTo _bodyGroup) then {
        _x ctrlSetPosition [0, 0, _compactW, _compactH];
        _x ctrlCommit 0;
    };
} forEach allControls _bodyGroup;
private _patient = _display getVariable ["ACME_SK_ReturnPatient", objNull];
if (isNull _patient) then {_patient = ACE_player;};
// Create dynamic clinical overlays before click controls, so new art cannot cover the input layer.
[_bodyGroup, _patient, -1] call ace_medical_gui_fnc_updateBodyImage;
// Runtime overlays were just created. Hide them with the group until Body Map is selected.
_bodyGroup ctrlShow false;
_display setVariable ["ACME_SK_BodyVisible", false];
private _inputs = [];
{
    _x params ["", "_part", "_site", "_image", "_id"];
    _inputs pushBack [_id, _part, _site, _image, true];
} forEach (call ACME_fnc_skSiteGeometry);
{
    _x params ["_part", "_image", "_id"];
    _inputs pushBack [_id, _part, -1, _image, false];
} forEach (call ACME_fnc_skIMGeometry);
{
    _x params ["_id", "_part", "_site", "_image", "_vascular"];
    private _c = _display ctrlCreate ["ACME_SK_HotspotButton", _id];
    _c setVariable ["ACME_SK_Target", [_part, _site, _image, _vascular]];
    _c ctrlSetText "";
    _c ctrlShow false;
    _c ctrlAddEventHandler ["MouseEnter", {(_this select 0) setVariable ["ACME_SK_Hover", true]; call ACME_fnc_skBuildHotspots;}];
    _c ctrlAddEventHandler ["MouseExit", {(_this select 0) setVariable ["ACME_SK_Hover", false]; call ACME_fnc_skBuildHotspots;}];
    _c ctrlAddEventHandler ["ButtonClick", {_this call ACME_fnc_skSiteClick;}];
} forEach _inputs;

// the body-injection layer: a body map view that injects the shared carousel-selected syringe at a site.
// Create toolbar controls after the native body group and site hitboxes. The group
// includes transparent canvas below the feet that overlaps most of the route row;
// creating it later intercepted clicks and left only the buttons' bottom edges active.
// Keep the original full button rectangles above that canvas in both views.
private _tw = _uiW / 11;
private _th = safeZoneH / 32;
private _tx = _uiX + (_uiW / 2) - (_tw / 2);
private _patientHeader = _display displayCtrl 84002;
if (!isNull _patientHeader) then {_display setVariable ["ACME_SK_PatientHeaderNativeRect", +(ctrlPosition _patientHeader)];};
private _viewY  = safeZoneY + (safeZoneH / 1.08);  // restored to the original low Draw Syringe / Body Map row.
private _routeY = safeZoneY + (safeZoneH * 0.748);

// Three-page navigation. On the Narc Box page the left button goes to Transfuse and the right button to Body Map.
// Body Map reverses the local page on the left and continues to Transfuse on the right. Both backings pulse without
// owning focus, so switching pages never magnetizes the cursor to a newly recreated control.
private _navGap = 4 * pixelW;
private _navW = _tw * 0.72;
private _navLeftX = (_uiX + (_uiW/2)) - (_navGap/2) - _navW;
private _navRightX = (_uiX + (_uiW/2)) + (_navGap/2);
private _pulseBack = _display ctrlCreate ["RscText", 84153];
_pulseBack ctrlSetPosition [_navLeftX, _viewY, _navW, _th];
_pulseBack ctrlSetBackgroundColor (["info", 0.45] call ACME_fnc_a11yColor);
_pulseBack ctrlCommit 0;
private _pulseBackR = _display ctrlCreate ["RscText", 84157];
_pulseBackR ctrlSetPosition [_navRightX, _viewY, _navW, _th];
_pulseBackR ctrlSetBackgroundColor (["info", 0.45] call ACME_fnc_a11yColor);
_pulseBackR ctrlCommit 0;

private _toggleBtn = _display ctrlCreate ["ACME_SK_PulseButton", 84150];
_toggleBtn ctrlSetPosition [_navLeftX, _viewY, _navW, _th];
_toggleBtn ctrlSetText "< Transfuse";
_toggleBtn ctrlSetTooltip "Previous page";
_toggleBtn ctrlAddEventHandler ["ButtonClick", {["left"] call ACME_fnc_skPageNavigate;}];
_toggleBtn ctrlCommit 0;
private _toggleBtnR = _display ctrlCreate ["ACME_SK_PulseButton", 84152];
_toggleBtnR ctrlSetPosition [_navRightX, _viewY, _navW, _th];
_toggleBtnR ctrlSetText "Body Map >";
_toggleBtnR ctrlSetTooltip "Next page";
_toggleBtnR ctrlAddEventHandler ["ButtonClick", {["right"] call ACME_fnc_skPageNavigate;}];
_toggleBtnR ctrlCommit 0;

// B76 contextual action directly above Draw Syringe. The backing owns the blinking red/green color so hover/focus
// cannot freeze it; the transparent button owns only text/input.
private _bodyActionY = _viewY - _th - safeZoneH*0.006;
private _bodyActionBack = _display ctrlCreate ["RscText",84819];
_bodyActionBack ctrlSetPosition [_tx,_bodyActionY,_tw,_th];
_bodyActionBack ctrlShow false; _bodyActionBack ctrlCommit 0;
private _bodyAction = _display ctrlCreate ["ACME_SK_PulseButton",84820];
_bodyAction ctrlSetPosition [_tx,_bodyActionY,_tw,_th];
_bodyAction ctrlSetText "Discard Syringe";
_bodyAction ctrlShow false;
_bodyAction ctrlAddEventHandler ["ButtonClick",{call ACME_fnc_skBodyActionClick;}];
_bodyAction ctrlCommit 0;

// Capture ACM's live 10/5/3/1 syringe canvas scale and plunger travel.  The carousel selected item uses this
// native geometry, so it is exactly the same visual scale as ACM/ACME's normal draw syringe rather than a guessed
// screen fraction.  Travel is normalized to the 10 mL travel and re-scaled per stored syringe size.
private _nativeBarrel = _display displayCtrl (84010 + 3 * (([10,5,3,1] find (uiNamespace getVariable ["ACME_SK_CurSize",10])) max 0) + 2);
if (!isNull _nativeBarrel) then {_display setVariable ["ACME_SK_CarouselNativeRect", ctrlPosition _nativeBarrel];};
private _travelNow = (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitBottom",0]) - (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop",0]);
private _curRatio = switch (uiNamespace getVariable ["ACME_SK_CurSize",10]) do {case 1:{10.2/10.5};case 3:{9.83/10.5};case 5:{10.3/10.5};default{1};};
if (_travelNow > 0) then {_display setVariable ["ACME_SK_CarouselTravel10", _travelNow / (_curRatio max 0.01)];};

// B63: the explicit Open/Close Syringe Menu button remains retired. A/D or clicking a syringe promotes the carousel.
// A wide invisible retention zone spans the complete carousel workspace between the route row and Draw button.
// It is created underneath the actual syringe hitboxes so it can hold an expanded carousel open without stealing
// clicks from the visible syringes, Edit Tag, route buttons, or Done.
private _carouselZone = _display ctrlCreate ["ACME_SK_HotspotButton", 84481];
_carouselZone ctrlShow false;
_carouselZone ctrlAddEventHandler ["MouseEnter", {
    uiNamespace setVariable ["ACME_SK_CarouselZoneHover", true];
    if (uiNamespace getVariable ["ACME_SK_CarouselExpanded",false]) then {
        uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",diag_tickTime+0.85];
    };
}];
_carouselZone ctrlAddEventHandler ["MouseExit", {
    uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
    if (uiNamespace getVariable ["ACME_SK_CarouselExpanded",false]) then {
        uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",diag_tickTime+0.70];
    };
}];

// B62 tandem carousel. Five visual slots are always the same controls; compact/expanded rendering only changes
// their geometry. All five hitboxes also participate in the wide retention zone while the pointer is over them.
for "_slot" from 0 to 4 do {
    private _baseId = 84400 + (_slot * 10);
    { private _c = _display ctrlCreate ["RscPicture", _baseId + _x]; _c ctrlShow false; } forEach [0,1,2,3];
    { private _t = _display ctrlCreate ["ACME_SK_TagText", _baseId + _x]; _t ctrlShow false; _t ctrlSetBackgroundColor [0,0,0,0]; } forEach [4,5,6];
    private _hit = _display ctrlCreate ["ACME_SK_HotspotButton", _baseId + 8];
    _hit ctrlShow false;
    _hit setVariable ["ACME_SK_CarouselOffset", _slot - 2];
    _hit ctrlAddEventHandler ["MouseEnter", {
        private _c = _this select 0;
        uiNamespace setVariable ["ACME_SK_CarouselZoneHover", true];
        uiNamespace setVariable ["ACME_SK_CarouselHoverOffset", _c getVariable ["ACME_SK_CarouselOffset",99]];
        [true] call ACME_fnc_skCarouselHover;
    }];
    _hit ctrlAddEventHandler ["MouseExit", {
        private _c = _this select 0;
        if ((uiNamespace getVariable ["ACME_SK_CarouselHoverOffset",99]) == (_c getVariable ["ACME_SK_CarouselOffset",99])) then {
            uiNamespace setVariable ["ACME_SK_CarouselHoverOffset", 99];
        };
        uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
        [false] call ACME_fnc_skCarouselHover;
    }];
    _hit ctrlAddEventHandler ["ButtonClick", {
        private _c = _this select 0;
        [_c getVariable ["ACME_SK_CarouselOffset",0]] call ACME_fnc_skCarouselPick;
    }];
};
// A dedicated top-layer hover/click target for the active syringe prevents overlapping neighbor hitboxes from
// stealing MouseEnter on ultrawide layouts. Its render-time rectangle is deliberately more forgiving than the art.
private _activeHit = _display ctrlCreate ["ACME_SK_HotspotButton", 84480];
_activeHit ctrlShow false;
_activeHit setVariable ["ACME_SK_CarouselOffset", 0];
_activeHit ctrlAddEventHandler ["MouseEnter", {uiNamespace setVariable ["ACME_SK_CarouselZoneHover",true]; uiNamespace setVariable ["ACME_SK_CarouselHoverOffset",0]; [true] call ACME_fnc_skCarouselHover;}];
_activeHit ctrlAddEventHandler ["MouseExit", {if ((uiNamespace getVariable ["ACME_SK_CarouselHoverOffset",99]) == 0) then {uiNamespace setVariable ["ACME_SK_CarouselHoverOffset",99];}; uiNamespace setVariable ["ACME_SK_CarouselZoneHover",false]; [false] call ACME_fnc_skCarouselHover;}];
_activeHit ctrlAddEventHandler ["ButtonClick", {[0] call ACME_fnc_skCarouselPick;}];

// B64: noninteractive A/D + arrow hints flank the carousel.  Dynamic layout/render scales them with compact vs
// promoted carousel states; they never participate in hit testing.
private _leftKeyHint = _display ctrlCreate ["ACME_SK_StyledLabel", 84700];
_leftKeyHint ctrlSetText "A"; _leftKeyHint ctrlEnable false; _leftKeyHint ctrlShow false;
private _leftArrowHint = _display ctrlCreate ["ACME_SK_StyledLabel", 84701];
_leftArrowHint ctrlSetText "◀"; _leftArrowHint ctrlSetBackgroundColor [0,0,0,0]; _leftArrowHint ctrlEnable false; _leftArrowHint ctrlShow false;
private _rightArrowHint = _display ctrlCreate ["ACME_SK_StyledLabel", 84702];
_rightArrowHint ctrlSetText "▶"; _rightArrowHint ctrlSetBackgroundColor [0,0,0,0]; _rightArrowHint ctrlEnable false; _rightArrowHint ctrlShow false;
private _rightKeyHint = _display ctrlCreate ["ACME_SK_StyledLabel", 84703];
_rightKeyHint ctrlSetText "D"; _rightKeyHint ctrlEnable false; _rightKeyHint ctrlShow false;

// Three invisible editors remain attached to the active stored syringe while the carousel is expanded.
for "_line" from 0 to 2 do {
    private _e = _display ctrlCreate ["ACME_SK_TagEdit", 84460 + _line];
    _e ctrlShow false;
    _e ctrlAddEventHandler ["KillFocus", {call ACME_fnc_skTagCommit}];
    _e ctrlAddEventHandler ["KeyUp", {call ACME_fnc_skTagCommit}];
    _e ctrlAddEventHandler ["MouseEnter", {[true] call ACME_fnc_skCarouselHover;}];
    _e ctrlAddEventHandler ["MouseExit", {[false] call ACME_fnc_skCarouselHover;}];
};
private _colorBtn = _display ctrlCreate ["ACME_SK_StyledButton", 84470];
_colorBtn ctrlSetText "Edit Syringe Tag";
_colorBtn ctrlShow false;
_colorBtn ctrlAddEventHandler ["ButtonClick", {
    private _d = findDisplay 84000;
    if (isNull _d) exitWith {};
    if !(uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {call ACME_fnc_skTagEditOpen;};
    private _l = _d displayCtrl 84471;
    if (ctrlShown _l) then {
        _l lbSetCurSel -1;
        _l ctrlShow false;
        ctrlSetFocus (_d displayCtrl 84460);
    } else {
        _l lbSetCurSel -1;
        _l ctrlShow true;
        ctrlSetFocus _l;
    };
}];
_colorBtn ctrlAddEventHandler ["MouseEnter", {uiNamespace setVariable ["ACME_SK_CarouselZoneHover",true];}];
_colorBtn ctrlAddEventHandler ["MouseExit", {uiNamespace setVariable ["ACME_SK_CarouselZoneHover",false];}];
private _colorList = _display ctrlCreate ["ACME_SK_TagList", 84471];
_colorList ctrlShow false;
{
    _x params ["_id","_label"];
    private _i = _colorList lbAdd _label;
    _colorList lbSetData [_i,_id];
} forEach [
    ["none","None - No syringe tag"],
    ["yellow_induction","Yellow - Induction agents"],
    ["orange_benzodiazepine","Orange - Benzodiazepines / sedatives"],
    ["blue_opioid","Light blue - Opioids / narcotics"],
    ["blue_stripe_reversal","Blue/white stripe - Opioid antagonists"],
    ["red_paralytic","Red - Paralytics / muscle relaxants"],
    ["red_stripe_reversal","Red/white stripe - Paralytic reversal"],
    ["violet_vasopressor","Violet - Vasopressors"],
    ["violet_stripe_hypotensive","Violet/white stripe - Hypotensive agents"],
    ["green_anticholinergic","Green - Anticholinergics"],
    ["gray_local_anesthetic","Gray - Local anesthetics"],
    ["salmon_antiemetic","Salmon / pink - Antiemetics"],
    ["white_saline_flush","White - Saline / diluent / maintenance"]
];
// Keep LBSelChanged, but also commit on MouseButtonUp. The second path makes single-click selection robust on
// clients where focus/z-order prevented the listbox selection event from being observed reliably.
_colorList ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skTagColor}];
_colorList ctrlAddEventHandler ["MouseButtonUp", {
    params ["_ctrl"];
    private _row = lbCurSel _ctrl;
    if (_row >= 0) then {[_ctrl,_row] call ACME_fnc_skTagColor;};
}];
_colorList ctrlAddEventHandler ["MouseEnter", {uiNamespace setVariable ["ACME_SK_CarouselZoneHover",true];}];
_colorList ctrlAddEventHandler ["MouseExit", {uiNamespace setVariable ["ACME_SK_CarouselZoneHover",false];}];

private _tagDone = _display ctrlCreate ["ACME_SK_StyledButton", 84472];
_tagDone ctrlSetText "Done";
_tagDone ctrlSetTooltip "Save tag edits and return to the Body Map";
_tagDone ctrlSetPosition [_tx,_viewY,_tw,_th];
_tagDone ctrlShow false;
_tagDone ctrlAddEventHandler ["ButtonClick", {call ACME_fnc_skTagEditDone;}];
_tagDone ctrlCommit 0;

// B71 Body Map injection status. Created after the carousel/tag controls so "Pushing..." always renders on top.
// fn_skCarouselRender owns its exact position between Edit Syringe Tag and the active syringe.
private _pushStatus = _display ctrlCreate ["ACME_SK_StyledLabel", 84810];
_pushStatus ctrlSetText "Pushing...";
_pushStatus ctrlSetBackgroundColor [0,0,0,0];
_pushStatus ctrlSetTextColor [1,1,1,1];
_pushStatus ctrlEnable false;
_pushStatus ctrlShow false;
_pushStatus ctrlCommit 0;


// A/D controls the same stable syringe selection in either the full carousel or Body Map mini-carousel. The keys
// remain ordinary text input whenever an edit control, including push duration, owns focus.
_display displayAddEventHandler ["KeyDown", {
    params ["_d","_key"];
    private _view = uiNamespace getVariable ["ACME_SK_View", "syringe"];
    if (_view != "body") exitWith {false};
    private _focus = focusedCtrl _d;
    if (!isNull _focus && {ctrlType _focus == 2}) exitWith {
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir",0];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt",0];
        false
    };
    if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {_key in [30,32]};
    private _dir = switch (_key) do {case 30: {-1}; case 32: {1}; default {0};};
    if (_dir == 0) exitWith {false};
    // Engine key-repeat differs between clients. Own the hold cadence so carousel motion stays deterministic.
    if ((uiNamespace getVariable ["ACME_SK_CarouselHeldDir", 0]) != _dir) then {
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir", _dir];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt", diag_tickTime + 0.22];
        [_dir] call ACME_fnc_skCarouselMove;
    };
    true
}];
_display displayAddEventHandler ["KeyUp", {
    params ["_d","_key"];
    private _focus = focusedCtrl _d;
    if (!isNull _focus && {ctrlType _focus == 2}) exitWith {
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir",0];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt",0];
        false
    };
    if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {_key in [30,32]};
    private _dir = switch (_key) do {case 30: {-1}; case 32: {1}; default {0};};
    if (_dir == 0) exitWith {false};
    if ((uiNamespace getVariable ["ACME_SK_CarouselHeldDir", 0]) == _dir) then {
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir", 0];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt", 0];
    };
    (uiNamespace getVariable ["ACME_SK_View", "syringe"]) == "body"
}];

// Split route selector: backgrounds and input buttons have identical full-row geometry.
// Backings precede their buttons so selected colors do not intercept any part of a click.
private _routeGap = 2 * pixelW;
private _routeHalf = (_tw - _routeGap) / 2;
private _routeIVBack = _display ctrlCreate ["RscText", 84155];
_routeIVBack ctrlSetPosition [_tx, _routeY, _routeHalf, _th];
_routeIVBack ctrlShow false;
_routeIVBack ctrlCommit 0;
private _routeIMBack = _display ctrlCreate ["RscText", 84156];
_routeIMBack ctrlSetPosition [_tx + _routeHalf + _routeGap, _routeY, _routeHalf, _th];
_routeIMBack ctrlShow false;
_routeIMBack ctrlCommit 0;
private _routeBtn = _display ctrlCreate ["ACME_SK_PulseButton", 84151];
_routeBtn ctrlSetPosition [_tx, _routeY, _routeHalf, _th];
_routeBtn ctrlSetText "IV / IO";
_routeBtn ctrlSetTooltip "Use the selected IV or IO access";
_routeBtn ctrlAddEventHandler ["ButtonClick", {uiNamespace setVariable ["ACME_SK_Route", "vascular"]; uiNamespace setVariable ["ACME_SK_PendingInjection",[]]; call ACME_fnc_skBuildHotspots; call ACME_fnc_skBodyActionRender;}];
_routeBtn ctrlShow false;
_routeBtn ctrlCommit 0;
private _routeIM = _display ctrlCreate ["ACME_SK_PulseButton", 84154];
_routeIM ctrlSetPosition [_tx + _routeHalf + _routeGap, _routeY, _routeHalf, _th];
_routeIM ctrlSetText "IM";
_routeIM ctrlSetTooltip "Use an intramuscular injection site";
_routeIM ctrlAddEventHandler ["ButtonClick", {
    // IM cannot use a saline-flush route. Clear any stale flush selection before changing route so a previous
    // preparation session cannot immediately force the body map back to vascular mode.
    uiNamespace setVariable ["ACME_SK_SelFlush", ""];
    uiNamespace setVariable ["ACME_SK_Route", "im"];
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    call ACME_fnc_skBuildHotspots;
    call ACME_fnc_skBodyActionRender;
}];
_routeIM ctrlShow false;
_routeIM ctrlCommit 0;

// Keep the old right-hand button position, with Draw's exact width and height.
private _saveRect = +(ctrlPosition (_display displayCtrl 84005));
private _drawRect = ctrlPosition (_display displayCtrl 84003);
_saveRect set [2, _drawRect select 2];
_saveRect set [3, _drawRect select 3];
_display setVariable ["ACME_SK_SaveRect", _saveRect];
(_display displayCtrl 84004) ctrlSetPosition _saveRect;
(_display displayCtrl 84004) ctrlCommit 0;
(_display displayCtrl 84005) ctrlShow false;
(_display displayCtrl 84005) ctrlEnable false;
// B63: Draw and Save physically depress while held, then spring back.  The press rectangle is captured on each
// MouseButtonDown so later mode/layout changes cannot leave a stale restore position behind.
{
    private _pressBtn = _display displayCtrl _x;
    if (!isNull _pressBtn && {!(_pressBtn getVariable ["ACME_SK_PressFeedbackBound",false])}) then {
        _pressBtn setVariable ["ACME_SK_PressFeedbackBound",true];
        _pressBtn ctrlAddEventHandler ["MouseButtonDown", {
            params ["_c"];
            private _r = +(ctrlPosition _c);
            _c setVariable ["ACME_SK_PressBaseRect",_r];
            private _dx = 2*pixelW; private _dy = 2*pixelH;
            _c ctrlSetPosition [(_r select 0)+_dx,(_r select 1)+_dy,((_r select 2)-2*_dx) max (10*pixelW),((_r select 3)-_dy) max (8*pixelH)];
            _c ctrlCommit 0;
        }];
        _pressBtn ctrlAddEventHandler ["MouseButtonUp", {
            params ["_c"];
            private _r = _c getVariable ["ACME_SK_PressBaseRect",[]];
            if (_r isEqualType [] && {count _r == 4}) then {_c ctrlSetPosition _r; _c ctrlCommit 0.07;};
        }];
        _pressBtn ctrlAddEventHandler ["MouseExit", {
            params ["_c"];
            private _r = _c getVariable ["ACME_SK_PressBaseRect",[]];
            if (_r isEqualType [] && {count _r == 4}) then {_c ctrlSetPosition _r; _c ctrlCommit 0.07;};
        }];
    };
} forEach [84003,84004];
// Draw and Save also retain their configured button sounds. Callback replacement cannot mute them.
private _afterSaveId = uiNamespace getVariable ["ACME_SK_OpenBodyAfterSaveId", ""];
private _openStoredId = uiNamespace getVariable ["ACME_SK_OpenCarouselId", ""];
uiNamespace setVariable ["ACME_SK_CarouselExpanded", false];
uiNamespace setVariable ["ACME_SK_CarouselHover", false];
uiNamespace setVariable ["ACME_SK_CarouselHoverOffset", 99];
uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
uiNamespace setVariable ["ACME_SK_TagEditMode", false];
uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", 0];
uiNamespace setVariable ["ACME_SK_PendingInjection", []];
uiNamespace setVariable ["ACME_SK_DiscardArmedId", ""];
if (_afterSaveId != "") then {
    uiNamespace setVariable ["ACME_SK_OpenBodyAfterSaveId", ""];
    private _openStore = [ACE_player] call ACME_fnc_skStoreEnsureIds;
    [_afterSaveId, _openStore] call ACME_fnc_skSelectStored;
    uiNamespace setVariable ["ACME_SK_View", "body"];
} else {
    if (_openStoredId != "") then {
        uiNamespace setVariable ["ACME_SK_OpenCarouselId", ""];
        private _openStore = [ACE_player] call ACME_fnc_skStoreEnsureIds;
        if (([_openStoredId, _openStore] call ACME_fnc_skSelectStored) >= 0) then {
            uiNamespace setVariable ["ACME_SK_View", "body"];
            uiNamespace setVariable ["ACME_SK_CarouselExpanded", true];
            uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", diag_tickTime + 0.95];
        } else {
            uiNamespace setVariable ["ACME_SK_View", "syringe"];
        };
    } else {
        private _openStoredLegacy = uiNamespace getVariable ["ACME_SK_OpenCarouselIndex", -1];
        if (_openStoredLegacy >= 0) then {
            uiNamespace setVariable ["ACME_SK_OpenCarouselIndex", -1];
            private _openStore = [ACE_player] call ACME_fnc_skStoreEnsureIds;
            [_openStoredLegacy, _openStore] call ACME_fnc_skSelectStored;
            uiNamespace setVariable ["ACME_SK_View", "body"];
            uiNamespace setVariable ["ACME_SK_CarouselExpanded", true];
            uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", diag_tickTime + 0.95];
        } else {
            uiNamespace setVariable ["ACME_SK_View", "syringe"];
        };
    };
};
private _requestedView = uiNamespace getVariable ["ACME_SK_RequestedView",""];
if (_requestedView in ["syringe","body"]) then {
    uiNamespace setVariable ["ACME_SK_RequestedView",""];
    uiNamespace setVariable ["ACME_SK_View",_requestedView];
};
uiNamespace setVariable ["ACME_SK_Route", "vascular"];
_display setVariable ["ACME_SK_NextRefresh", 0];
_display setVariable ["ACME_SK_NextStockRefresh", 0];
_display setVariable ["ACME_SK_NextMedStock", 0];
_display setVariable ["ACME_SK_NextPendingTag", 0];
call ACME_fnc_skListRefresh;

// B71: main tag controls are deliberately deferred until fn_skOpenDraw finishes native control injection.
// fn_skPendingTagEnsure then creates them idempotently with artwork -> selector -> dropdown z-order.

call ACME_fnc_skSetView;
// B121: if a one-handed Hardcore push survived this dialog being closed, reopening the Narc Box is only a
// presentation change. Rebuild the exact patient/site/syringe context without touching the running PFH.
private _hcPushJobB121 = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if (_hcPushJobB121 isEqualType createHashMap && {count _hcPushJobB121 > 0}) then {call ACME_fnc_hardcorePushRestoreUi;};
// Native syringe controls can finish their first layout a frame after our runtime controls are created.
// Repaint the always-present Select Syringe Tag control again after that layout so it cannot disappear on first open.
[{if (!isNull (findDisplay 84000)) then {call ACME_fnc_skPendingTagRender;};}, [], 0.03] call CBA_fnc_waitAndExecute;
private _oldPulse = uiNamespace getVariable ["ACME_SK_PulsePFH", -1];
if (_oldPulse >= 0) then {[_oldPulse] call CBA_fnc_removePerFrameHandler;};
private _pulse = [{_this call ACME_fnc_skUiTick;}, 0.04, [_display]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_SK_PulsePFH", _pulse];
