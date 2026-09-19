disableSerialization;
private _display = findDisplay 84000;
if (isNull _display) exitWith {};
private _view = uiNamespace getVariable ["ACME_SK_View", "syringe"];
// B62 compatibility: an old callback that asks for the retired standalone carousel opens the tandem Body Map
// with its carousel expanded instead.
if (_view == "carousel") then {
    _view = "body";
    uiNamespace setVariable ["ACME_SK_View", "body"];
    uiNamespace setVariable ["ACME_SK_CarouselExpanded", true];
};
private _body = _view == "body";
private _infusion = !((_display getVariable ["ACME_SK_Return", []]) isEqualTo []);
if (_infusion) then {_body = false; _view = "syringe"; uiNamespace setVariable ["ACME_SK_View", "syringe"];};
private _size = uiNamespace getVariable ["ACME_SK_CurSize", 10];
private _base = 84010 + 3 * (([10,5,3,1] find _size) max 0);

// Native draw controls exist only on the preparation page.
{(_display displayCtrl _x) ctrlShow (!_body);} forEach [84003,84009,_base,_base+1,_base+2];
(_display displayCtrl 84004) ctrlShow (!_body && {!_infusion} && {(uiNamespace getVariable ["ACME_SK_WasteStage", ""]) in ["compound","draw"]});
(_display displayCtrl 84005) ctrlShow _infusion;
(_display displayCtrl 84005) ctrlEnable _infusion;
(_display displayCtrl 84006) ctrlShow false;
// B69: Body Map is a dedicated administration page. Preparation sources return only with Draw Syringe.
(_display displayCtrl 84007) ctrlShow (!_infusion && {!_body});
(_display displayCtrl 84008) ctrlShow (!_body);
(_display displayCtrl 84129) ctrlShow (!_body);
(_display displayCtrl 84131) ctrlShow (!_infusion && {!_body});

// Body Map route row remains present while the carousel changes size beneath it.
{(_display displayCtrl _x) ctrlShow _body;} forEach [84151,84154,84155,84156];

if (!_infusion) then {
    private _leftPage = _display displayCtrl 84150;
    private _rightPage = _display displayCtrl 84152;
    if (_body) then {
        _leftPage ctrlSetText "< Narc Box";
        _leftPage ctrlSetTooltip "Return to syringe preparation";
        _rightPage ctrlSetText "Transfuse >";
        _rightPage ctrlSetTooltip "Open Transfuse Fluids";
    } else {
        _leftPage ctrlSetText "< Transfuse";
        _leftPage ctrlSetTooltip "Open Transfuse Fluids";
        _rightPage ctrlSetText "Body Map >";
        _rightPage ctrlSetTooltip "Open the body injection map";
    };
    { _x ctrlShow true; _x ctrlEnable true; } forEach [_leftPage,_rightPage];
} else {
    {(_display displayCtrl _x) ctrlShow false;} forEach [84150,84152,84153,84157];
};

// B59 mini-carousel controls remain retired; B62 uses only the adaptive 84400-series carousel.
for "_slot" from 0 to 2 do {{(_display displayCtrl (84500 + _slot*10 + _x)) ctrlShow false;} forEach [0,1,2,3,4,5,6];};
{(_display displayCtrl _x) ctrlShow false;} forEach [84540,84541,84542];

if (_body) then {
    // B71 the pending Draw Syringe tag editor never belongs on Body Map, including during first-frame control repair.
    {(_display displayCtrl _x) ctrlShow false;} forEach [84600,84601,84602,84603,84610,84611];
    (_display displayCtrl 84001) ctrlSetText "";
    call ACME_fnc_skDynamicLayout;
    call ACME_fnc_skCarouselRender;
    call ACME_fnc_skBodyActionRender;
} else {
    (_display displayCtrl 84810) ctrlShow false;
    (_display displayCtrl 84819) ctrlShow false;
    (_display displayCtrl 84820) ctrlShow false;
    (_display displayCtrl 84830) ctrlShow false;
    (_display displayCtrl 84831) ctrlShow false;
    (_display displayCtrl 84832) ctrlShow false;
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    uiNamespace setVariable ["ACME_SK_DiscardArmedId",""];
    uiNamespace setVariable ["ACME_SK_TagEditMode", false];
    uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
    // Hide the tandem carousel and restore native header ownership on the preparation page.
    for "_slot" from 0 to 4 do {{(_display displayCtrl (84400 + _slot*10 + _x)) ctrlShow false;} forEach [0,1,2,3,4,5,6,8];};
    {(_display displayCtrl _x) ctrlShow false;} forEach [84460,84461,84462,84470,84471,84472,84480,84481,84700,84701,84702,84703,84810];
    private _patientHeader = _display displayCtrl 84002;
    if (!isNull _patientHeader) then {
        private _hr = _display getVariable ["ACME_SK_PatientHeaderNativeRect", []];
        if (_hr isEqualType [] && {count _hr == 4}) then {_patientHeader ctrlSetPosition _hr; _patientHeader ctrlCommit 0;};
    };
    if (!_infusion) then {
        private _p = _display getVariable ["ACME_SK_ReturnPatient", objNull];
        if (isNull _p) then {_p = uiNamespace getVariable ["ACME_SK_Patient", objNull];};
        (_display displayCtrl 84001) ctrlSetText "No Medication Selected";
        private _pn = if (isNull _p) then {""} else {name _p};
        (_display displayCtrl 84002) ctrlSetText format ["%1 %2", _pn, uiNamespace getVariable ["ACME_SK_BodyPart",""]];
    };
};
call ACME_fnc_skPendingTagRender;
call ACME_fnc_skBuildHotspots;
call ACME_fnc_skListRefresh;
