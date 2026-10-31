// the "Spike Y tubing" button in the transfusion menu, for blood only. it builds a prepared y-type iv set, with
// the blood, saline and y tubing all consumed into a stored set, over three presses. the set is hung later from
// the prepared iv sets list, through prepared iv sets, select set, hang set, rather than here.
// press 1, with blood selected and nothing pending, requires a y-tubing set on hand and remembers the blood in
// ACME_yPending. the button relabels to "Select Flush Saline". Native donor bags carry their configured
// donor ID into the prepared set. Used fresh-blood rows must be hung directly; they are refused here.
// press 2, with a valid ACM saline selected and blood pending, remembers the saline in ACME_yPendingSaline.
// nothing is consumed yet and the button relabels to "Build Y Tubing".
// press 3, with both pending, consumes the y tubing, blood and saline out of the kit and stores a ready prepared
// iv set on the medic, in ACME_preparedIVSets. the cold state of the blood is recorded, so it still hangs
// [cooled] when it goes up.
params [["_coolerResume",[]]];
private _medic = ACE_player;
if (isNull _medic || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
if (ACE_player getVariable ["ACME_persistenceFrozen",false]) exitWith {};
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (!isNull _target && {_target getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
private _right = _display displayCtrl 86005;
private _clearPairing = {
        missionNamespace setVariable ["ACME_yPending", ""];
        missionNamespace setVariable ["ACME_yPendingData", ""];
        missionNamespace setVariable ["ACME_yPendingSaline", ""];
        missionNamespace setVariable ["ACME_yPendingSalineData", ""];
        missionNamespace setVariable ["ACME_yPendingBloodVol", 0];
        missionNamespace setVariable ["ACME_yPendingSalineVol", 0];
        missionNamespace setVariable ["ACME_yPendingBloodUsedId", ""];
        missionNamespace setVariable ["ACME_yPendingSalineUsedId", ""];
        missionNamespace setVariable ["ACME_yPendingBloodUsedRow", []];
        missionNamespace setVariable ["ACME_yPendingSalineUsedRow", []];
        missionNamespace setVariable ["ACME_yPendingPatient", objNull];
        missionNamespace setVariable ["ACME_ySelExactVol", 0];
        missionNamespace setVariable ["ACME_ySelUsedId", ""];
        missionNamespace setVariable ["ACME_ySelUsedRow", []];
};
private _coolerContext=[ACE_player,_target,
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0],
    ACE_player getVariable ["ACME_equipmentKitEpoch",0],
    ACE_player getVariable ["ACME_providerLocalityEpoch",0],
    missionNamespace getVariable ["ACME_yPending",""],
    missionNamespace getVariable ["ACME_yPendingSaline",""],
    missionNamespace getVariable ["ACME_yPendingData",""],
    missionNamespace getVariable ["ACME_yPendingSalineData",""],
    missionNamespace getVariable ["ACME_yPendingBloodUsedId",""],
    missionNamespace getVariable ["ACME_yPendingSalineUsedId",""],
    if (isNull _target) then {-1} else {[_target] call ACME_fnc_clinicalEpoch}];
if (_coolerResume isNotEqualTo [] && {_coolerResume isNotEqualTo _coolerContext}) exitWith {};
private _drawing=missionNamespace getVariable ["ACME_yCoolerDrawPending",[]];
if (_drawing isNotEqualTo [] && {(_drawing select 1) isNotEqualTo _coolerContext}) then {
    missionNamespace setVariable ["ACME_yCoolerDrawPending",[]];
    _drawing=[];
};
if (_drawing isNotEqualTo [] && {_coolerResume isEqualTo []}) exitWith {};

// CBA's delayed job uses mission time, which can pause while diag_tickTime
// advances. Only the pending request may release this recipe, never a wall
// clock deadline. This also prevents a new recipe during callback re-entry.
if ((missionNamespace getVariable ["ACME_yBuildPending",[]]) isNotEqualTo []) exitWith {};
private _idx = lbCurSel _right;
private _data = if (_idx >= 0) then { _right lbData _idx } else { "" };

// a used-bag row, marked |USED, is not a real inventory item and carries the fluid type where the build expects
// an item class. we do not materialize it here, because doing that at selection meant switching menus mid-build
// converted and consumed the bag. instead we derive the real item class, so the type and blood are right, and
// remember the bag, with its exact remaining volume and store id. nothing is added to the kit and nothing is
// removed from the store until the build actually commits, at press 3. it is gated on having a y-tubing set, so
// we do not bother when the build cannot proceed.
private _usedSelection = (_data splitString "|");
private _usedFresh = false;
if ((_usedSelection param [2,""]) == "USED") then {
    private _used = ACE_player getVariable ["ACME_usedBags",[]];
    private _index = _used findIf {(_x param [0,""]) == (_usedSelection param [3,""])};
    _usedFresh = _index >= 0 && {((_used select _index) param [1,""]) in ["FreshBlood","FBTK"]};
};
if (_usedFresh) exitWith {["Fresh donor blood must be hung directly; it cannot be converted into a stored Y set.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;};
missionNamespace setVariable ["ACME_ySelExactVol", 0];
missionNamespace setVariable ["ACME_ySelUsedId", ""];
missionNamespace setVariable ["ACME_ySelUsedRow", []];
if ((((_data splitString "|") param [2, ""]) == "USED") && {([ACE_player, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) >= 1}) then {
    private _uid = (_data splitString "|") param [3, ""];
    private _used = ACE_player getVariable ["ACME_usedBags", []];
    private _ui = _used findIf { (_x param [0, ""]) isEqualTo _uid };
    if (_ui >= 0) then {
        (_used select _ui) params [["_uid2", ""], ["_utype", ""], ["_urem", 0], ["_uat", 0], ["_ubt", -1], ["_uorig", 1000], ["_unm", ""]];
        // normalize to a valid ACM fluid type for the item class. a pulled y saline reserve is stored as ACME_SalineY,
        // and fresh blood as FreshBlood or FBTK, and neither is a real item type.
        private _matType = _utype;
        if (_utype == "ACME_SalineY") then { _matType = "Saline"; };
        if (_utype in ["FreshBlood", "FBTK"]) then { _matType = "Blood"; };
        // formatfluidbagname can name a class that is not actually defined, at an odd size, so verify it. fall back to
        // the smallest existing standard size that still covers the remaining volume, because a 100 ml used saline must
        // not balloon into a 1000 ml item, and then to the largest existing size as a last resort. the blood type, _ubt,
        // is carried through, so o- stays o-.
        private _itemClass = [_matType, _uorig, _ubt] call ACM_circulation_fnc_formatFluidBagName;
        if (_itemClass == "" || {!isClass (configFile >> "CfgWeapons" >> _itemClass)}) then {
            private _fitting = "";
            private _largest = "";
            {
                private _c = [_matType, _x, _ubt] call ACM_circulation_fnc_formatFluidBagName;
                if (_c != "" && {isClass (configFile >> "CfgWeapons" >> _c)}) then {
                    _largest = _c;
                    if (_fitting == "" && {_x >= _urem}) then { _fitting = _c; };
                };
            } forEach [50, 100, 250, 500, 1000];
            _itemClass = [_fitting, _largest] select (_fitting == "");
        };
        if (_itemClass != "" && {isClass (configFile >> "CfgWeapons" >> _itemClass)}) then {
            _data = format ["%1|", _itemClass];  // the real item class. the action is re-derived from the fluid tables downstream.
            missionNamespace setVariable ["ACME_ySelExactVol", _urem];
            missionNamespace setVariable ["ACME_ySelUsedId", _uid];
            missionNamespace setVariable ["ACME_ySelUsedRow", +(_used select _ui)];
        } else {
            ["Could not ready the used bag for a Y build (no matching bag size).", 4.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
        };
    };
};
private _parts = _data splitString "|";
private _selClass  = _parts param [0, ""];
private _selAction = _parts param [1, ""];
// the FBTK is never a y-set component, because it is a native single-bag blood-collection kit. it is rejected
// outright here. the button is also hidden for it in fn_updatetransfusioncontrols, so this is belt and
// suspenders.
if ((_selClass find "FieldBloodTransfusionKit") >= 0) exitWith {
    ["Field blood transfusion kits are not built into Y sets. Attach it on its own to collect blood.", 4, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _isBlood  = ((_selClass find "FieldBloodTransfusionKit") < 0) && {((toLowerANSI _selClass) find "blood") >= 0};
private _isSaline = (_selClass != "") && {[_selClass, _selAction] call ACME_fnc_isSalineItem};
private _pending       = missionNamespace getVariable ["ACME_yPending", ""];
private _pendingSaline = missionNamespace getVariable ["ACME_yPendingSaline", ""];
if (_pending != "" && {(missionNamespace getVariable ["ACME_yPendingPatient", _target]) isNotEqualTo _target}) exitWith {
    call _clearPairing;
    call ACME_fnc_transfusionFilterInventory;
    ["Patient changed. Select the Y-set components again.", 3, ACE_player] call ace_common_fnc_displayTextStructured;
};

// press 1: arm the blood for the set.
if (_pending isEqualTo "") exitWith {
    if (!_isBlood) exitWith { ["Select a blood unit first, then press Spike Y tubing.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured; };
    // fresh whole blood, where a filled FBTK becomes an fwb bag with uniquebag=1, is allowed into a y set now. its
    // per-unit data lives in the global acm_circulation_freshbloodlist registry, which is not pruned when the item
    // leaves the inventory, and ivbag and ivbaglocal read it back by the id carried in the classname. so a consumed
    // fwb unit still hangs at its real collected volume and type. the raw, empty FBTK collection kit is still
    // refused above, caught by the FieldBloodTransfusionKit guard near the top, which matches the rule that y tubing
    // comes only after it fills.
    if (([ACE_player, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        ["You need a Y-type blood tubing set to build a Y line.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    missionNamespace setVariable ["ACME_yPending", _selClass];
    missionNamespace setVariable ["ACME_yPendingPatient", _target];
    missionNamespace setVariable ["ACME_yPendingData", _data];  // the full "item|action" for the blood.
    missionNamespace setVariable ["ACME_yPendingBloodVol", missionNamespace getVariable ["ACME_ySelExactVol", 0]];
    missionNamespace setVariable ["ACME_yPendingBloodUsedId", missionNamespace getVariable ["ACME_ySelUsedId", ""]];
    missionNamespace setVariable ["ACME_yPendingBloodUsedRow", missionNamespace getVariable ["ACME_ySelUsedRow", []]];
    call ACME_fnc_transfusionFilterInventory;
    call ACME_fnc_updateTransfusionControls;
    ["Y set: select the saline to pair, then press Select Flush Saline.", 3.5, ACE_player] call ace_common_fnc_displayTextStructured;
};

// press 2: remember the saline for the set. nothing is consumed yet.
if (_pendingSaline isEqualTo "") exitWith {
    if (!_isSaline) exitWith { ["Pick a proper ACM saline bag to pair with the blood.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured; };
    missionNamespace setVariable ["ACME_yPendingSaline", _selClass];
    missionNamespace setVariable ["ACME_yPendingSalineData", _data];
    missionNamespace setVariable ["ACME_yPendingSalineVol", missionNamespace getVariable ["ACME_ySelExactVol", 0]];
    missionNamespace setVariable ["ACME_yPendingSalineUsedId", missionNamespace getVariable ["ACME_ySelUsedId", ""]];
    missionNamespace setVariable ["ACME_yPendingSalineUsedRow", missionNamespace getVariable ["ACME_ySelUsedRow", []]];
    call ACME_fnc_transfusionFilterInventory;
    call ACME_fnc_updateTransfusionControls;
    ["Saline paired. Press Build Y Tubing to assemble the set.", 3.5, ACE_player] call ace_common_fnc_displayTextStructured;
};

// press 3: build the set. it consumes the y tubing, blood and saline and stores it, and it does not hang it.
private _blood = _pending;
private _bloodData = missionNamespace getVariable ["ACME_yPendingData", ""];
private _bloodAction = (_bloodData splitString "|") param [1, ""];
private _saline = _pendingSaline;
private _salineData = missionNamespace getVariable ["ACME_yPendingSalineData", ""];
private _salineAction = (_salineData splitString "|") param [1, ""];
private _bloodExactVol  = missionNamespace getVariable ["ACME_yPendingBloodVol", 0];
private _salineExactVol = missionNamespace getVariable ["ACME_yPendingSalineVol", 0];
private _bloodUsedId  = missionNamespace getVariable ["ACME_yPendingBloodUsedId", ""];
private _salineUsedId = missionNamespace getVariable ["ACME_yPendingSalineUsedId", ""];

private _fnc_clearPending = {
    call _clearPairing;
    call ACME_fnc_transfusionFilterInventory;
};

if (([ACE_player, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    call _fnc_clearPending;
    ["Y-type tubing unavailable. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// Used legs stay in their virtual store through the whole build beat. A native
// nominal-size item can never represent their exact remaining volume.
private _usedRows = ACE_player getVariable ["ACME_usedBags",[]];
private _usedValid = true;
private _resolveUsed = {
    params ["_uid","_kinds","_volume","_saved"];
    if (_uid == "") exitWith {[]};
    private _found = _usedRows select {(_x param [0,""]) == _uid};
    if (count _found != 1) exitWith {_usedValid = false; []};
    private _row = _found select 0;
    if (count _row < 7 || {!((_row select 1) in _kinds)} || {!((_row select 2) isEqualType 0)}
        || {!finite (_row select 2)} || {(_row select 2) <= 0} || {(_row select 2) != _volume}
        || {!((_row select 5) isEqualType 0)} || {!finite (_row select 5)} || {(_row select 5) <= 0} || {(_row select 2) > (_row select 5)}
        || {!((_row select 4) isEqualType 0)} || {!finite (_row select 4)}
        || {_saved isNotEqualTo [] && {_row isNotEqualTo _saved}}) exitWith {_usedValid = false; []};
    +_row
};
private _bloodUsedRow = [_bloodUsedId,["Blood"],_bloodExactVol,missionNamespace getVariable ["ACME_yPendingBloodUsedRow",[]]] call _resolveUsed;
private _salineUsedRow = [_salineUsedId,["Saline","ACME_SalineY"],_salineExactVol,missionNamespace getVariable ["ACME_yPendingSalineUsedRow",[]]] call _resolveUsed;
if (!_usedValid || {_bloodUsedId != "" && {_bloodUsedId == _salineUsedId}}) exitWith {
    call _fnc_clearPending;
    ["A selected used bag changed or is no longer available. Build canceled; remaining bags are kept.",4,ACE_player] call ace_common_fnc_displayTextStructured;
};

// re-derive the live action of the blood from the current list by class, which mirrors the old direct-hang
// guard, so a stale press-1 snapshot is corrected. that happens when a unit slid between a loose row and a
// [cooled] row while the medic stepped away. it falls back to the press-1 snapshot if the class is not
// currently listed, and the cooler-pull below still recovers it.
private _liveAction = "";
private _liveCooler = false;
for "_r" from 0 to ((lbSize _right) - 1) do {
    if (_liveAction == "") then {
        private _rd = (_right lbData _r) splitString "|";
        if ((_rd param [0, ""]) == _blood) then {
            _liveAction = _rd param [1, ""];
            _liveCooler = (_rd param [2, ""]) == "COOLER";
        };
    };
};
if (_liveAction != "") then {
    _bloodAction = _liveAction;
    _bloodData = format ["%1|%2%3", _blood, _liveAction, ["", "|COOLER"] select _liveCooler];
};

// The canonical carrier/box claim owns this debit. Compatibility mirrors are
// read-only projections and can never fund a Y build.
private _bloodFromCooler = _coolerResume isNotEqualTo [] || {((_bloodData splitString "|") param [2, ""]) == "COOLER"};
if (_bloodUsedId isNotEqualTo "") then {_bloodFromCooler=false;};
if (_bloodFromCooler && {_coolerResume isEqualTo []}) exitWith {
    private _serial=(missionNamespace getVariable ["ACME_yCoolerDrawSerial",0])+1;
    missionNamespace setVariable ["ACME_yCoolerDrawSerial",_serial];
    missionNamespace setVariable ["ACME_yCoolerDrawPending",[_serial,_coolerContext]];
    private _queued=[ACE_player,_blood,[ACME_fnc_coolerYDrawDone,[_serial,_coolerContext]]] call ACME_fnc_coolerDraw;
    if (!_queued) then {[false,[_serial,_coolerContext]] call ACME_fnc_coolerYDrawDone;};
};
if (_bloodUsedId == "" && {([ACE_player, _target, _blood] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {
    call _fnc_clearPending;
    ["Blood unit not on hand. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (_salineUsedId == "" && {([ACE_player, _target, _saline] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {
    call _fnc_clearPending;
    ["Saline bag not on hand. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// the build beat. assembling the set takes a moment. the y button shows "Building...", rendered by
// fn_updatetransfusioncontrols while the exact pending request owns this recipe. The callback below consumes
// the items and stores the set. Intent and busy fences stay owned through source settlement and cleanup.
private _buildSerial = 1 + (missionNamespace getVariable ["ACME_yBuildSerial",0]);
missionNamespace setVariable ["ACME_yBuildSerial",_buildSerial];
missionNamespace setVariable ["ACME_yBuildPending",[_buildSerial,_coolerContext]];
ACE_player setVariable ["ACME_yBuildPending",[_buildSerial,_coolerContext select 6,_coolerContext select 7],true];
missionNamespace setVariable ["ACME_yBuildingActive", diag_tickTime + 2.5];
// Register before presentation. A broken/rebuilding display cannot prevent
// the already-owned request from reaching cancellation or source settlement.
[{
    params ["_blood", "_bloodAction", "_saline", "_salineAction", "_bloodFromCooler", ["_bloodExactVol", 0], ["_salineExactVol", 0], ["_medic", objNull], ["_target", objNull], ["_bloodPersonal", false], ["_salinePersonal", false], ["_bloodUsedRow",[]], ["_salineUsedRow",[]], ["_buildSerial",-1], ["_buildContext",[]]];
    private _request = [_buildSerial,_buildContext];
    private _releaseBusy = {
        if (!isNull _medic && {(_medic getVariable ["ACME_yBuildPending",[]]) isEqualTo [_buildSerial,_buildContext select 6,_buildContext select 7]}) then {_medic setVariable ["ACME_yBuildPending",[],true];};
    };
    // A replay or superseded request can retire only its own provider fence.
    // It cannot clear another request's recipe, timer or presentation.
    if ((missionNamespace getVariable ["ACME_yBuildPending",[]]) isNotEqualTo _request) exitWith {call _releaseBusy;};
    private _success = false;
    private _notice = "";
    isNil {
        private _currentTarget = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
        private _currentContext = [_medic,_currentTarget,
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0],
            if (isNull _medic) then {-1} else {_medic getVariable ["ACME_equipmentKitEpoch",0]},
            if (isNull _medic) then {-1} else {_medic getVariable ["ACME_providerLocalityEpoch",0]},
            missionNamespace getVariable ["ACME_yPending",""],missionNamespace getVariable ["ACME_yPendingSaline",""],
            missionNamespace getVariable ["ACME_yPendingData",""],missionNamespace getVariable ["ACME_yPendingSalineData",""],
            missionNamespace getVariable ["ACME_yPendingBloodUsedId",""],missionNamespace getVariable ["ACME_yPendingSalineUsedId",""],
            if (isNull _currentTarget) then {-1} else {[_currentTarget] call ACME_fnc_clinicalEpoch}];
        if (_currentContext isNotEqualTo _buildContext || {isNull (findDisplay 86000)} || {_medic isNotEqualTo ACE_player}
            || {uiNamespace getVariable ["ACME_preparedListMode",false]} || {(missionNamespace getVariable ["ACME_piggybackPending",[]]) isNotEqualTo []}) exitWith {};
        if (isNull _medic || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious",false]}
            || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}
            || {!isNull _target && {([_medic,_target] call ACME_fnc_patientInteractionDistance) > 5}}) exitWith {};
        if (_medic getVariable ["ACME_persistenceFrozen",false] || {!isNull _target && {_target getVariable ["ACME_persistenceFrozen",false]}}) exitWith {};
        if (([_medic, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {_notice = "Y-type tubing unavailable. Build canceled.";};
        if (_bloodUsedRow isEqualTo [] && {([_medic, _target, _blood] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {_notice = "Blood unit not on hand. Build canceled.";};
        if (_salineUsedRow isEqualTo [] && {([_medic, _target, _saline] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {_notice = "Saline bag not on hand. Build canceled.";};

        // Both exact virtual rows and all physical legs are checked/debited in
        // one unscheduled operation. There are no presentation calls here.
        private _usedBefore = +(_medic getVariable ["ACME_usedBags",[]]);
        private _usedAfter = +_usedBefore;
        private _usedOK = true;
        {
            if (_x isNotEqualTo []) then {
                private _source = _x;
                private _matches = _usedAfter select {(_x param [0,""]) == (_source select 0)};
                if (count _matches != 1 || {(_matches select 0) isNotEqualTo _source}) exitWith {_usedOK = false;};
                private _i = _usedAfter findIf {(_x select 0) == (_source select 0)};
                _usedAfter deleteAt _i;
            };
        } forEach [_bloodUsedRow,_salineUsedRow];
        if (!_usedOK) exitWith {_notice = "A selected used bag changed. Build canceled; remaining bags are kept.";};
        private _requirements = ["ACME_YTubing"];
        if (_bloodUsedRow isEqualTo []) then {_requirements pushBack [_blood,_bloodPersonal];};
        if (_salineUsedRow isEqualTo []) then {_requirements pushBack [_saline,_salinePersonal];};
        private _receipts = [_medic,_target,_requirements] call ACME_fnc_treatmentSupplyTakeMany;
        if (_receipts isEqualTo []) exitWith {_notice = "A Y-set component is no longer available. Build canceled; used bags are kept.";};

// the nominal full volume, parsed from the class suffix, such as ACM_BloodBag_..._500 or ACE_salineIV_500, where
// a bare ace_salineiv is 1000. it is a label only, so an odd class name harmlessly defaults to 1000.
private _fnc_vol = {
    params ["_cls"];
    private _p = _cls splitString "_";
    private _tok = _p param [(count _p) - 1, ""];
    private _n = parseNumber _tok;
    if (_n >= 1 && {(str _n) == _tok}) then { _n } else { 1000 }
};
private _bVol = [_blood] call _fnc_vol;
private _sVol = [_saline] call _fnc_vol;

private _bcfg = configFile >> "CfgWeapons" >> _blood;
private _bName = [getText (_bcfg >> "displayName"), getText (_bcfg >> "shortName")] select (isText (_bcfg >> "shortName"));
if (_bName isEqualTo "") then { _bName = _blood; };
// a used leg carries its actual remaining volume, so the label must show that rather than the item-class size.
// rewrite the "(500ml)" part of the blood display name and the saline ml with the exact pulled amounts.
if (_bloodExactVol > 0) then {
    private _paren = _bName find " (";
    if (_paren >= 0) then {_bName = _bName select [0,_paren];};
    _bName = _bName + format [" (%1ml)", round _bloodExactVol];
};
private _sVolShown = if (_salineExactVol > 0) then { round _salineExactVol } else { _sVol };
private _coldTag = ["", " [Cooled]"] select _bloodFromCooler;
private _label = format ["%1 + Saline %2mL%3", _bName, _sVolShown, _coldTag];

// the record is [id, bloodclass, bloodaction, salineclass, salineaction, tiednetid, label, bloodcold]. a
// tiednetid of "" means untied, so it hangs on anyone. a freshly built set is always untied, and the
// remove-to-list feature, later, ties a set to the casualty it came off. bloodaction and salineaction are the
// live hang-action strings, and hang set re-derives them from the fluid tables at hang time and uses these as
// the fallback.
private _serial = (missionNamespace getVariable ["ACME_preparedItemSerial",0])+1;
missionNamespace setVariable ["ACME_preparedItemSerial",_serial];
private _id = format ["yset:%1:%2:%3",clientOwner,netId _medic,_serial];
private _rec = [_id, _blood, _bloodAction, _saline, _salineAction, "", _label, _bloodFromCooler, "yset", _bloodExactVol, _salineExactVol];
private _setsBefore = +(_medic getVariable ["ACME_preparedIVSets", []]);
private _sets = +_setsBefore;
_sets pushBack _rec;
_medic setVariable ["ACME_preparedIVSets", _sets, true];
_medic setVariable ["ACME_usedBags",_usedAfter,true];
        private _committed = [_medic] call ACME_fnc_preparedInventoryCommit;
        if (isNil "_committed" || {!_committed}) exitWith {
            _medic setVariable ["ACME_preparedIVSets",_setsBefore,true];
            _medic setVariable ["ACME_usedBags",_usedBefore,true];
            {[_x] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
            _notice = "The Y set could not be prepared. Its components are kept.";
            true
        };
        {[_x,false] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
        _success = true;
        true
    };
    // Ownership lasts through source settlement and raw intent cleanup. Only
    // then can another click begin work. UI failures cannot retain save fences.
    private _owned = (missionNamespace getVariable ["ACME_yBuildPending",[]]) isEqualTo _request;
    if (_owned) then {
        missionNamespace setVariable ["ACME_yPending", ""];
        missionNamespace setVariable ["ACME_yPendingData", ""];
        missionNamespace setVariable ["ACME_yPendingSaline", ""];
        missionNamespace setVariable ["ACME_yPendingSalineData", ""];
        missionNamespace setVariable ["ACME_yPendingBloodVol", 0];
        missionNamespace setVariable ["ACME_yPendingSalineVol", 0];
        missionNamespace setVariable ["ACME_yPendingBloodUsedId", ""];
        missionNamespace setVariable ["ACME_yPendingSalineUsedId", ""];
        missionNamespace setVariable ["ACME_yPendingBloodUsedRow", []];
        missionNamespace setVariable ["ACME_yPendingSalineUsedRow", []];
        missionNamespace setVariable ["ACME_yPendingPatient", objNull];
        missionNamespace setVariable ["ACME_ySelExactVol", 0];
        missionNamespace setVariable ["ACME_ySelUsedId", ""];
        missionNamespace setVariable ["ACME_ySelUsedRow", []];
        missionNamespace setVariable ["ACME_yBuildPending",[]];
        missionNamespace setVariable ["ACME_yBuildingActive",-1];
    };
    call _releaseBusy;
    if (!_owned || {isNull (findDisplay 86000)} || {_medic isNotEqualTo ACE_player}) exitWith {};
    call ACME_fnc_transfusionFilterInventory;
    if (_notice != "") then {[_notice,3,_medic] call ace_common_fnc_displayTextStructured;};
    if (_success) then {
        uiNamespace setVariable ["ACME_usedRowSig","__force__"];
        uiNamespace setVariable ["ACME_preparedRowSig","__force__"];
        ["Y set built. Preparing the IV set.",2,_medic] call ace_common_fnc_displayTextStructured;
        // All products stay in carried custody; no patient bag is hung here.
        [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
        [true] call ACME_fnc_togglePreparedSets;
    } else {
        call ACME_fnc_updateTransfusionControls;
    };
}, [_blood, _bloodAction, _saline, _salineAction, _bloodFromCooler, _bloodExactVol, _salineExactVol, ACE_player, _target, (_bloodFromCooler || {_bloodUsedId != ""}), (_salineUsedId != ""),_bloodUsedRow,_salineUsedRow,_buildSerial,_coolerContext], 2.5] call CBA_fnc_waitAndExecute;
call ACME_fnc_updateTransfusionControls;
["Building Y set...", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
