// this is driven by the renamed spike bag button in the transfusion menu.
// it has two behaviors in loose-bag mode.
// 1. an in-place y refill, where the button reads "Add Bag". if the access line of the selected blood already
// carries a y line, hang the next unit straight onto it, dropping the spent [empty blood bag] marker and
// keeping the clamped saline reserve. this is the one in-place hang that remains, and it matches the original
// add bag behavior.
// 2. spike into stage, where the button reads "Spike Bag". any other bag is spiked with an administration set,
// which consumes one ACME_IVLine, and staged into the prepared iv sets of the medic as a single-bag set tagged
// by kind: "blood", "saline" or "premixed". it is later hung from the prepared list through hang set, in
// fn_hangpreparedset, which enforces the one-line-per-access-site rule.
// y blood sets are built on the separate spike y tubing button, in fn_transfusionytubing, as kind "yset".
private _display = findDisplay 86000;
if (isNull _display) exitWith {};

// prepared iv sets mode. the button is relabeled "Hang Set" and the list shows the stored sets, in overlay
// 86145. route the press to the set-hang path instead of the spike and stage logic below.
if (uiNamespace getVariable ["ACME_preparedListMode", false]) exitWith { call ACME_fnc_hangPreparedSet; };

private _right = _display displayCtrl 86005;  // idc_transfusionmenu_rightlistpanel, the available bags.
private _idx = lbCurSel _right;
if (_idx < 0) exitWith {
    ["Select a bag first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _class = ((_right lbData _idx) splitString "|") param [0, ""];
if (_class isEqualTo "") exitWith {};

// the FBTK, the field blood transfusion kit, is not a blood product to pre-stage and it is not a y set. it is
// hung as a single bag that collects the patient's own blood, then becomes a usable blood unit when removed.
// that is native ACM behavior end to end. the spike, stage and y logic below treats anything whose class
// contains "blood" as a blood product, and fieldbloodtransfusionkit trips that, which broke it. so the kit is
// handed straight to ACM's native add bag, which hangs it to fill, and the removal is likewise handed to native
// in fn_transfusionpullbag, so it returns the filled blood. native addbag reads the same right-list selection
// this function does, so the pick carries over.
if ((_class find "FieldBloodTransfusionKit") >= 0) exitWith { call ACM_circulation_fnc_TransfusionMenu_AddBag; };

private _action = ((_right lbData _idx) splitString "|") param [1, ""];
// is it a cooler-sourced row? the available-list rows we add for cooler blood carry a trailing |COOLER
// marker.
private _fromCooler = ((((_right lbData _idx) splitString "|") param [2, ""]) == "COOLER");
// is it a used-bag row? the rows we add for pulled partial bags carry a |USED marker and the store id.
private _fromUsed = ((((_right lbData _idx) splitString "|") param [2, ""]) == "USED");

// re-hang a used bag. rebuild the pulled bag on the selected access with its exact remaining volume. the hung-bag
// entry is pushed straight onto IV_Bags, because the flow is derived from IV_Bags, so it hangs and runs from
// where it was left. a used ACME_SalineY keeps that type, so it re-hangs as the clamped y reserve, and onto an
// already-y'd site it simply joins the y. this branch fully owns the used case and never falls through to the
// loose-bag paths below.
if (_fromUsed) exitWith {
    private _usedId=(((_right lbData _idx) splitString "|") param [3,""]);
    private _target2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    private _bp2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
    private _iv2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
    private _site2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
    if (isNull _target2 || {_bp2==""} || {_site2<0}) exitWith {["Select an access site to hang the used bag on.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;};
    private _used=ACE_player getVariable ["ACME_usedBags",[]]; private _ui=_used findIf {(_x param [0,""])==_usedId}; if (_ui<0) exitWith {};
    private _record=+(_used select _ui);
    // Reserve locally before the network round-trip. A rejected owner transaction restores this exact record.
    _used deleteAt _ui; ACE_player setVariable ["ACME_usedBags",_used,true];
    private _requestId=format ["rehang:%1:%2:%3",clientOwner,diag_frameNo,floor(diag_tickTime*1000)];
    private _pending=uiNamespace getVariable ["ACME_usedRehangPending",createHashMap]; _pending set [_requestId,_record]; uiNamespace setVariable ["ACME_usedRehangPending",_pending]; uiNamespace setVariable ["ACME_usedRowSig","__force__"];
    private _warmer=([ACE_player,"ACME_BloodWarmer"] call ACME_fnc_itemCount)>=1;
    [_target2,"rehangUsedBag",[_target2,ACE_player,_bp2,_iv2,_site2,_usedId,_record,[_target2] call ACME_fnc_clinicalEpoch,_requestId,_warmer]] call ACME_fnc_ownerDispatch;
};

private _isBlood  = ((toLowerANSI _class) find "blood")  >= 0;
private _isSaline = ((toLowerANSI _class) find "saline") >= 0;
// the kind stored on a staged single-bag set: saline, blood or premixed, where premixed is any other carrier such
// as PlasmaLyte, mannitol, HTS or magnesium. only saline sets can become an infusion, through prep infusion, and
// blood and premixed are grayed.
private _kind = "premixed";
if (_isSaline) then { _kind = "saline"; } else { if (_isBlood) then { _kind = "blood"; }; };

private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];

// a blood unit that is mid-y-pairing, armed for a y set, must not be spiked out from under the build.
if (_isBlood && {(missionNamespace getVariable ["ACME_yPending", ""]) == _class}) exitWith {
    ["This blood is armed for a Y set. Finish or clear the Y build first.", 3.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// a cooler draw to hand. a |COOLER selection has no loose bag, so draw the unit out now, from a carried cooler or
// a box within reach, and it becomes a normal loose unit for either the y refill or the spike and stage below.
// _fromCooler tells us it is cold. it only fires when nothing of this class is already loose, because a loose bag
// is always used first.
if (_isBlood && _fromCooler && {([ACE_player, _class] call ACME_fnc_itemCount) < 1}) then {
    private _cstore = ACE_player getVariable ["ACME_coolerStore", createHashMap];
    private _heldNow = ((uniformItems ACE_player) + (vestItems ACE_player) + (backpackItems ACE_player)) select { (_x find "ACME_BloodCooler_") == 0 };
    private _gotIt = false;
    {
        if (_gotIt) exitWith {};
        private _cc = _x;
        if (_cc in _heldNow) then {
            private _contents = _cstore getOrDefault [_cc, []];
            private _hit = _contents findIf { (_x param [0, ""]) isEqualTo _class };
            if (_hit >= 0) then { _contents deleteAt _hit; _cstore set [_cc, _contents]; [ACE_player, "store", _cstore, true] call ACME_fnc_coolerStateCommit; _gotIt = true; };
        };
    } forEach (keys _cstore);
    if (!_gotIt) then {
        {
            if (_gotIt) exitWith {};
            private _bx = _x;
            private _cargo = itemCargo _bx;
            private _i = _cargo find _class;
            if (_i >= 0) then { _cargo deleteAt _i; clearItemCargoGlobal _bx; { _bx addItemCargoGlobal [_x, 1]; } forEach _cargo; _gotIt = true; };
        } forEach (nearestObjects [ACE_player, ["ACME_BloodCoolerBox_CSWB1U", "ACME_BloodCoolerBox_CSWB2U", "ACME_BloodCoolerBox_CSWB4U"], 6]);
    };
    if (_gotIt) then {
        missionNamespace setVariable ["ACME_coolerAutoStoreSuppressUntil", diag_tickTime + 5];
        missionNamespace setVariable ["ACME_coolerAutoStoreBusy", true];
        ACE_player addItem _class;
        if (([ACE_player, _class] call ACME_fnc_itemCount) < 1) then {
            private _cont = objNull;
            { if (!isNull _x) exitWith { _cont = _x; }; } forEach [backpackContainer ACE_player, vestContainer ACE_player, uniformContainer ACE_player];
            if (!isNull _cont) then { _cont addItemCargoGlobal [_class, 1]; };
        };
        missionNamespace setVariable ["ACME_coolerAutoStoreBusy", false];
        uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
        if (!isNull (uiNamespace getVariable ["ACME_CLR_DLG", displayNull])) then { call ACME_fnc_coolerRefresh; };
    };
};

// the in-place Y refill, "Add Bag". The provider UI does only advisory checks; the casualty owner reserves the
// exact Y access before ACM's native 5 s Add Bag action starts, then finalizes the replacement against the latest
// owner-side IV_Bags state. This prevents two medics from both consuming a replacement for the same empty leg.
private _yBodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _yIV   = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _ySite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _lineKey = toLowerANSI format ["%1#%2#%3", _yBodyPart, _yIV, _ySite];
private _lineYd = _lineKey in ((if (isNull _target) then {[]} else {_target getVariable ["ACME_YLines", []]}) apply {toLowerANSI _x});

private _requestYRefill = {
    params ["_mode"];
    if (isNull _target || {_yBodyPart == ""} || {_ySite < 0}) exitWith {
        ["Select the Y-line access first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    private _inventoryMode = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory", 0];
    // Cooler rows were materialized into the medic's inventory above before this claim is requested.
    if (_fromCooler) then {_inventoryMode = 0;};
    private _warmer = ([ACE_player, "ACME_BloodWarmer"] call ACME_fnc_itemCount) >= 1;
    private _epoch = [_target] call ACME_fnc_clinicalEpoch;
    private _requestId = format ["yrefill:%1:%2:%3", clientOwner, diag_frameNo, floor (diag_tickTime * 1000)];
    private _pending = uiNamespace getVariable ["ACME_yRefillPending", createHashMap];
    _pending set [_requestId, [_target,_mode,_class,_action,_yBodyPart,_yIV,_ySite,_epoch,_inventoryMode,_fromCooler,_warmer]];
    // Bound abandoned UI-side requests. Normal claim/cancel/done acknowledgements delete their own entry.
    private _keys = keys _pending;
    while {count _keys > 16} do {_pending deleteAt (_keys deleteAt 0);};
    uiNamespace setVariable ["ACME_yRefillPending", _pending];
    [_target, "yRefill", [_target,ACE_player,"claim",_requestId,_mode,_yBodyPart,_yIV,_ySite,_epoch,_fromCooler,_warmer]] call ACME_fnc_ownerDispatch;
};

if (_isBlood && _lineYd && {!isNull _target}) exitWith {
    // Local checks are only fast feedback. The casualty owner repeats every clinical/access check before granting.
    private _bags = (_target getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_yBodyPart, []];
    private _hasActiveBlood = (_bags findIf {
        ((_x param [0, ""]) in ["Blood", "FreshBlood"])
            && {(_x param [1, 0]) > 0.01}
            && {(_x param [3, -1]) == _ySite}
            && {(_x param [4, true]) isEqualTo _yIV}
    }) >= 0;
    if (_hasActiveBlood) exitWith {
        ["A unit is still running on this Y line.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    private _dirtyNow = (_target getVariable ["ACME_YLineDirty", createHashMap]) getOrDefault [_lineKey, false];
    if (_dirtyNow) exitWith {
        ["Flush the line (Flush Line) before hanging the next unit.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    if (([ACE_player, _class] call ACME_fnc_itemCount) < 1) exitWith {
        ["Blood unit not on hand.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    ["blood"] call _requestYRefill;
};

// Saline on a Y'd access becomes the clamped reserve only when that exact IV/IO site has no live reserve.
// Otherwise it falls through to normal Spike Bag behavior and remains usable as an ordinary additional saline bag.
private _yReserveLive = false;
if (_isSaline && _lineYd && {!isNull _target}) then {
    private _bpCheck = (_target getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_yBodyPart, []];
    _yReserveLive = (_bpCheck findIf {
        ((_x param [0, ""]) in ["ACME_SalineY", "Saline"])
            && {(_x param [1, 0]) > 0.5}
            && {(_x param [3, -1]) == _ySite}
            && {(_x param [4, true]) isEqualTo _yIV}
    }) >= 0;
};
if (_isSaline && _lineYd && {!isNull _target} && {!_yReserveLive}) exitWith {
    if (([ACE_player, _class] call ACME_fnc_itemCount) < 1) exitWith {
        ["Bag not on hand.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    ["saline"] call _requestYRefill;
};

// spike into stage. any bag not caught above is spiked and staged into the prepared iv sets.
private _setItem = "ACME_IVLine";
private _setName = "an IV line (administration set)";
if (([ACE_player, _setItem] call ACME_fnc_itemCount) < 1) exitWith {
    [format ["You need %1 to spike this bag.", _setName], 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (([ACE_player, _class] call ACME_fnc_itemCount) < 1) exitWith {
    ["Bag not on hand.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
// do not start a second spike while one is running.
if (count (missionNamespace getVariable ["ACME_spikingActive", []]) > 0) exitWith {};

// a "Spiking Bag..." beat on the button, then the commit, which consumes the iv line and the bag and stores a
// single-bag set.
missionNamespace setVariable ["ACME_spikingActive", [_class, diag_tickTime + 1.6]];
[{
    params ["_class", "_action", "_setItem", "_setName", "_kind", "_cold"];
    missionNamespace setVariable ["ACME_spikingActive", []];
    if (([ACE_player, _setItem] call ACME_fnc_itemCount) < 1) exitWith {
        [format ["%1 is no longer available.", _setName], 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    if (([ACE_player, _class] call ACME_fnc_itemCount) < 1) exitWith {
        ["The bag is no longer on hand.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    [ACE_player, _setItem] call ACME_fnc_itemTake;
    [ACE_player, _class] call ACME_fnc_itemTake;

    private _cfg = configFile >> "CfgWeapons" >> _class;
    private _nm = [getText (_cfg >> "displayName"), getText (_cfg >> "shortName")] select (isText (_cfg >> "shortName"));
    if (_nm isEqualTo "") then { _nm = _class; };
    private _label = format ["%1%2", _nm, ["", " [Cooled]"] select _cold];

    private _id = format ["set_%1_%2", floor (diag_tickTime * 1000), floor (random 100000)];
    private _rec = [_id, _class, _action, "", "", "", _label, _cold, _kind];
    private _sets = ACE_player getVariable ["ACME_preparedIVSets", []];
    _sets pushBack _rec;
    ACE_player setVariable ["ACME_preparedIVSets", _sets, true];
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];

    ["Bag spiked and staged to Prepared IV sets.", 2, ACE_player] call ace_common_fnc_displayTextStructured;

    if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
    };
}, [_class, _action, _setItem, _setName, _kind, (_isBlood && _fromCooler)], 1.6] call CBA_fnc_waitAndExecute;
