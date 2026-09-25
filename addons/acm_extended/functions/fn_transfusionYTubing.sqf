// the "Spike Y tubing" button in the transfusion menu, for blood only. it builds a prepared y-type iv set, with
// the blood, saline and y tubing all consumed into a stored set, over three presses. the set is hung later from
// the prepared iv sets list, through prepared iv sets, select set, hang set, rather than here.
// press 1, with blood selected and nothing pending, requires a y-tubing set on hand and remembers the blood in
// ACME_yPending. the button relabels to "Select Flush Saline". fresh blood units are refused, because their
// per-unit hang data cannot be rebuilt once the unit is consumed into a set, so only stored blood products,
// from a cooler or loose, are allowed.
// press 2, with a valid ACM saline selected and blood pending, remembers the saline in ACME_yPendingSaline.
// nothing is consumed yet and the button relabels to "Build Y Tubing".
// press 3, with both pending, consumes the y tubing, blood and saline out of the kit and stores a ready prepared
// iv set on the medic, in ACME_preparedIVSets. the cold state of the blood is recorded, so it still hangs
// [cooled] when it goes up.
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _right = _display displayCtrl 86005;
// a build beat is already running, so ignore further presses until it commits.
if (diag_tickTime < (missionNamespace getVariable ["ACME_yBuildingActive", -1])) exitWith {};
private _idx = lbCurSel _right;
private _data = if (_idx >= 0) then { _right lbData _idx } else { "" };

// a used-bag row, marked |USED, is not a real inventory item and carries the fluid type where the build expects
// an item class. we do not materialize it here, because doing that at selection meant switching menus mid-build
// converted and consumed the bag. instead we derive the real item class, so the type and blood are right, and
// remember the bag, with its exact remaining volume and store id. nothing is added to the kit and nothing is
// removed from the store until the build actually commits, at press 3. it is gated on having a y-tubing set, so
// we do not bother when the build cannot proceed.
missionNamespace setVariable ["ACME_ySelExactVol", 0];
missionNamespace setVariable ["ACME_ySelUsedId", ""];
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
    missionNamespace setVariable ["ACME_yPending", ""];
    missionNamespace setVariable ["ACME_yPendingSaline", ""];
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
    ["Y set: select the saline to pair, then press Select Flush Saline.", 3.5, ACE_player] call ace_common_fnc_displayTextStructured;
};

// press 2: remember the saline for the set. nothing is consumed yet.
if (_pendingSaline isEqualTo "") exitWith {
    if (!_isSaline) exitWith { ["Pick a proper ACM saline bag to pair with the blood.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured; };
    missionNamespace setVariable ["ACME_yPendingSaline", _selClass];
    missionNamespace setVariable ["ACME_yPendingSalineData", _data];
    missionNamespace setVariable ["ACME_yPendingSalineVol", missionNamespace getVariable ["ACME_ySelExactVol", 0]];
    missionNamespace setVariable ["ACME_yPendingSalineUsedId", missionNamespace getVariable ["ACME_ySelUsedId", ""]];
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
    missionNamespace setVariable ["ACME_yPending", ""];
    missionNamespace setVariable ["ACME_yPendingData", ""];
    missionNamespace setVariable ["ACME_yPendingSaline", ""];
    missionNamespace setVariable ["ACME_yPendingSalineData", ""];
    missionNamespace setVariable ["ACME_yPendingBloodUsedId", ""];
    missionNamespace setVariable ["ACME_yPendingSalineUsedId", ""];
};

if (([ACE_player, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    call _fnc_clearPending;
    ["Y-type tubing unavailable. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// materialize at commit time. only now, when the build is actually committing, do we turn any used-bag leg into
// a real item and remove it from the used-bag store. this is why arming a used bag and then switching menus
// never consumes it. a leg materializes only if it is confirmed on hand, and if it is not, because the kit is
// full, the build cancels and the bag is kept.
private _fnc_matUsed = {
    params ["_uid", "_cls"];
    if (_uid isEqualTo "") exitWith { true };  // not a used leg.
    if (([ACE_player, _cls] call ace_common_fnc_getCountOfItem) >= 1) exitWith { true };  // already on hand.
    private _used = ACE_player getVariable ["ACME_usedBags", []];
    private _ui = _used findIf { (_x param [0, ""]) isEqualTo _uid };
    if (_ui < 0) exitWith { false };  // the bag is gone from the store.
    // keep the cooler auto-store watcher off while the readied item sits loose in the kit, through the 2.5 s build
    // beat until the set consumes it. without this the watcher sweeps a readied blood unit into the cooler
    // mid-beat, the on-hand re-check of the build then cancels, and the used bags are lost. that was the reported
    // bug.
    missionNamespace setVariable ["ACME_coolerAutoStoreSuppressUntil", diag_tickTime + 8];
    missionNamespace setVariable ["ACME_coolerAutoStoreBusy", true];
    ACE_player addItem _cls;
    if (([ACE_player, _cls] call ace_common_fnc_getCountOfItem) < 1) then {
        private _cont = objNull;
        { if (!isNull _x) exitWith { _cont = _x; }; } forEach [backpackContainer ACE_player, vestContainer ACE_player, uniformContainer ACE_player];
        if (!isNull _cont) then { _cont addItemCargoGlobal [_cls, 1]; };
    };
    missionNamespace setVariable ["ACME_coolerAutoStoreBusy", false];
    if (([ACE_player, _cls] call ace_common_fnc_getCountOfItem) >= 1) then {
        _used deleteAt _ui;
        ACE_player setVariable ["ACME_usedBags", _used, true];
        uiNamespace setVariable ["ACME_usedRowSig", "__force__"];
        true
    } else { false }
};
if (!([_bloodUsedId, _blood] call _fnc_matUsed)) exitWith {
    call _fnc_clearPending;
    ["Could not ready the used blood (kit full). Build canceled; the bag is kept.", 4.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (!([_salineUsedId, _saline] call _fnc_matUsed)) exitWith {
    call _fnc_clearPending;
    ["Could not ready the used saline (kit full). Build canceled; the bag is kept.", 4.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
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

// cooler auto-use. a [cooled] blood selection lives in the cooler, either carried or in a nearby box, rather
// than in loose inventory, so pull one out to hand now and it can be consumed into the set. this is the same
// recovery block as the direct y build and spike-into-add. the cold state is stored on the set record below, so
// no ACME_ySetsCooled banking is needed here.
private _bloodFromCooler = ((_bloodData splitString "|") param [2, ""]) == "COOLER";
// a used-bag blood leg is a warm pulled unit already readied in hand. if the medic also has cooled blood of the
// same class, the re-derive above matches the [cooled] row and would mislabel this set [cooled], and try the
// cooler pull. force it off, because the used leg never comes from the cooler.
if (_bloodUsedId isNotEqualTo "") then { _bloodFromCooler = false; };
if (_bloodFromCooler && {([ACE_player, _blood] call ace_common_fnc_getCountOfItem) < 1}) then {
    private _cstore = ACE_player getVariable ["ACME_coolerStore", createHashMap];
    private _gotIt = false;
    // 1. a cooler the medic is carrying, which is a virtual store keyed by cooler class.
    {
        if (_gotIt) exitWith {};
        private _cc = _x;
        private _contents = _cstore getOrDefault [_cc, []];
        private _hit = _contents findIf { (_x param [0, ""]) isEqualTo _blood };
        if (_hit >= 0) then {
            _contents deleteAt _hit;
            _cstore set [_cc, _contents];
            [ACE_player, "store", _cstore, true] call ACME_fnc_coolerStateCommit;
            _gotIt = true;
        };
    } forEach (keys _cstore);
    // 2. a cooler box set down within reach, which is real cargo.
    if (!_gotIt) then {
        {
            if (_gotIt) exitWith {};
            private _bx = _x;
            private _cargo = itemCargo _bx;
            private _i = _cargo find _blood;
            if (_i >= 0) then {
                _cargo deleteAt _i;
                clearItemCargoGlobal _bx;
                { _bx addItemCargoGlobal [_x, 1]; } forEach _cargo;
                _gotIt = true;
            };
        } forEach (nearestObjects [ACE_player, ["ACME_BloodCoolerBox_CSWB1U", "ACME_BloodCoolerBox_CSWB2U", "ACME_BloodCoolerBox_CSWB4U"], 6]);
    };
    if (_gotIt) then {
        missionNamespace setVariable ["ACME_coolerAutoStoreSuppressUntil", diag_tickTime + 5];
        missionNamespace setVariable ["ACME_coolerAutoStoreBusy", true];
        ACE_player addItem _blood;
        // it is consumed into the set in this same action, so ignore the kit space. if additem did not take, because the
        // kit is full by ACM's slot accounting, force it into the cargo of a worn container, so it always lands and is
        // never lost.
        if (([ACE_player, _blood] call ace_common_fnc_getCountOfItem) < 1) then {
            private _cont = objNull;
            { if (!isNull _x) exitWith { _cont = _x; }; } forEach [backpackContainer ACE_player, vestContainer ACE_player, uniformContainer ACE_player];
            if (!isNull _cont) then { _cont addItemCargoGlobal [_blood, 1]; };
        };
        missionNamespace setVariable ["ACME_coolerAutoStoreBusy", false];
        uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
        if (!isNull (uiNamespace getVariable ["ACME_CLR_DLG", displayNull])) then { call ACME_fnc_coolerRefresh; };
    };
};
if (([ACE_player, _target, _blood] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    call _fnc_clearPending;
    ["Blood unit not on hand. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (([ACE_player, _target, _saline] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    call _fnc_clearPending;
    ["Saline bag not on hand. Build canceled.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// the build beat. assembling the set takes a moment. the y button shows "Building...", rendered by
// fn_updatetransfusioncontrols while ACME_yBuildingActive is in the future, and then the commit below consumes
// the items and stores the set. the pendings stay set during the beat, so the button state holds.
missionNamespace setVariable ["ACME_yBuildingActive", diag_tickTime + 2.5];
["Building Y set...", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
[{
    params ["_blood", "_bloodAction", "_saline", "_salineAction", "_bloodFromCooler", ["_bloodExactVol", 0], ["_salineExactVol", 0], ["_medic", objNull], ["_target", objNull], ["_bloodPersonal", false], ["_salinePersonal", false]];
    missionNamespace setVariable ["ACME_yBuildingActive", -1];
    private _fnc_clearPending = {
        missionNamespace setVariable ["ACME_yPending", ""];
        missionNamespace setVariable ["ACME_yPendingData", ""];
        missionNamespace setVariable ["ACME_yPendingSaline", ""];
        missionNamespace setVariable ["ACME_yPendingSalineData", ""];
        missionNamespace setVariable ["ACME_yPendingBloodUsedId", ""];
        missionNamespace setVariable ["ACME_yPendingSalineUsedId", ""];
    };
    if (isNull _medic || {!local _medic} || {!alive _medic}
        || {!isNull _target && {_medic distance _target > 5}}) exitWith {call _fnc_clearPending;};
    // re-check that everything is still on hand, because any piece could have been dropped mid-build.
    if (([_medic, _target, "ACME_YTubing"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        call _fnc_clearPending;
        ["Y-type tubing unavailable. Build canceled.", 3, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    if (([_medic, _target, _blood] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        call _fnc_clearPending;
        ["Blood unit not on hand. Build canceled.", 3, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    if (([_medic, _target, _saline] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        call _fnc_clearPending;
        ["Saline bag not on hand. Build canceled.", 3, _medic, 13] call ace_common_fnc_displayTextStructured;
    };

    // consume all three physical items into the set.
    private _receipts = [_medic, _target, ["ACME_YTubing", [_blood, _bloodPersonal], [_saline, _salinePersonal]]] call ACME_fnc_treatmentSupplyTakeMany;
    if (_receipts isEqualTo []) exitWith {
        call _fnc_clearPending;
        ["A Y-set component is no longer available. Build canceled.", 3, _medic] call ace_common_fnc_displayTextStructured;
    };
    {[_x, false] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;

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
    _bName = ([_bName, _bName select [0, _paren]] select (_paren >= 0)) + format [" (%1ml)", round _bloodExactVol];
};
private _sVolShown = if (_salineExactVol > 0) then { round _salineExactVol } else { _sVol };
private _coldTag = ["", " [Cooled]"] select _bloodFromCooler;
private _label = format ["%1 + Saline %2mL%3", _bName, _sVolShown, _coldTag];

// the record is [id, bloodclass, bloodaction, salineclass, salineaction, tiednetid, label, bloodcold]. a
// tiednetid of "" means untied, so it hangs on anyone. a freshly built set is always untied, and the
// remove-to-list feature, later, ties a set to the casualty it came off. bloodaction and salineaction are the
// live hang-action strings, and hang set re-derives them from the fluid tables at hang time and uses these as
// the fallback.
private _id = format ["yset_%1_%2", floor (diag_tickTime * 1000), floor (random 100000)];
private _rec = [_id, _blood, _bloodAction, _saline, _salineAction, "", _label, _bloodFromCooler, "yset", _bloodExactVol, _salineExactVol];
private _sets = _medic getVariable ["ACME_preparedIVSets", []];
_sets pushBack _rec;
_medic setVariable ["ACME_preparedIVSets", _sets, true];

    call _fnc_clearPending;
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];

    // refresh the available-bag list, so the consumed blood and saline drop off it immediately. the dialog stays
    // open, so the medic can build more sets. it resolves its own display, so it is safe to call from here.
    if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
    };


    ["Y set built. Open Prepared IV sets to hang it.", 4, _medic] call ace_common_fnc_displayTextStructured;
}, [_blood, _bloodAction, _saline, _salineAction, _bloodFromCooler, _bloodExactVol, _salineExactVol, ACE_player, _target, (_bloodFromCooler || {_bloodUsedId != ""}), (_salineUsedId != "")], 2.5] call CBA_fnc_waitAndExecute;
