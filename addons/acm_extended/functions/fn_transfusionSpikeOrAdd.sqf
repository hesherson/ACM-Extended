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
params [["_coolerResume",[]]];
if (ACE_player getVariable ["ACME_persistenceFrozen",false]) exitWith {};
private _display = findDisplay 86000;
if (isNull _display) exitWith {};

// prepared iv sets mode. the button is relabeled "Hang Set" and the list shows the stored sets, in overlay
// 86145. route the press to the set-hang path instead of the spike and stage logic below.
if (_coolerResume isEqualTo [] && {uiNamespace getVariable ["ACME_preparedListMode", false]}) exitWith { call ACME_fnc_hangPreparedSet; };

private _right = _display displayCtrl 86005;  // idc_transfusionmenu_rightlistpanel, the available bags.
private _idx = lbCurSel _right;
if (_idx < 0 && {_coolerResume isEqualTo []}) exitWith {
    ["Select a bag first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _class = if (_coolerResume isEqualTo []) then {((_right lbData _idx) splitString "|") param [0, ""]} else {_coolerResume select 0};
if (_class isEqualTo "") exitWith {};
private _action = if (_coolerResume isEqualTo []) then {((_right lbData _idx) splitString "|") param [1, ""]} else {_coolerResume select 1};

private _piggybackIntent = missionNamespace getVariable ["ACME_piggybackPending", []];
if !(_piggybackIntent isEqualTo []) then {
    private _same = count _piggybackIntent >= 6 && {(_piggybackIntent select [0,4]) isEqualTo [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]]};
    if (!_same) then {["cancel"] call ACME_fnc_piggybackWorkflow; _piggybackIntent = [];};
};
private _piggybackAllowed = true;
if !(_piggybackIntent isEqualTo []) then {
    private _candidateType = if ((_action find "FreshBloodBag_") == 0) then {"FreshBlood"} else {getText(configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type")};
    if (_action == "usedbag") then {_candidateType = _class;};
    _piggybackAllowed = count _piggybackIntent >= 6 && {[_piggybackIntent select 0,_piggybackIntent select 1,_piggybackIntent select 2,_piggybackIntent select 3,_candidateType] call ACME_fnc_piggybackEligible};
};
if (!_piggybackAllowed) exitWith {[ACE_player,"Select a fluid bag for the connected piggyback line."] call ACME_fnc_clinicalNotice;};

// Direct emulsion bottles enter Prepared Infusions with their own administration
// line. They never enter the generic saline-bag spike or Y-refill paths.
if (_class == "ACM_Vial_Propofol") exitWith {call ACME_fnc_spikePropofolBottle;};

// the FBTK, the field blood transfusion kit, is not a blood product to pre-stage and it is not a y set. it is
// hung as a single bag that collects the patient's own blood, then becomes a usable blood unit when removed.
// that is native ACM behavior end to end. the spike, stage and y logic below treats anything whose class
// contains "blood" as a blood product, and fieldbloodtransfusionkit trips that, which broke it. so the kit is
// handed straight to ACM's native add bag, which hangs it to fill, and the removal is likewise handed to native
// in fn_transfusionpullbag, so it returns the filled blood. native addbag reads the same right-list selection
// this function does, so the pick carries over.
if ((_class find "FieldBloodTransfusionKit") >= 0) exitWith { call ACME_fnc_fbtkHang; };

// is it a cooler-sourced row? the available-list rows we add for cooler blood carry a trailing |COOLER
// marker.
private _fromCooler = !(_coolerResume isEqualTo []) || {((((_right lbData _idx) splitString "|") param [2, ""]) == "COOLER")};
// is it a used-bag row? the rows we add for pulled partial bags carry a |USED marker and the store id.
private _fromUsed = _coolerResume isEqualTo [] && {((((_right lbData _idx) splitString "|") param [2, ""]) == "USED")};

private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _lineContext = if (isNil "ACME_fnc_getSelectedIVLineContext") then {[]} else {call ACME_fnc_getSelectedIVLineContext};
private _left = _display displayCtrl 86004;
private _leftRow = if (isNull _left) then {-1} else {lbCurSel _left};
private _leftValue = if (_leftRow < 0) then {-1} else {_left lbValue _leftRow};
private _lineSelection = if (_leftValue < 0) then {[]} else {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[]]) param [_leftValue,[]]};
if ((_lineSelection param [0, ""]) == "ACME_Line" && {_lineContext isEqualTo []}) exitWith {
    [ACE_player,"The selected IV line changed. Select its current entry before attaching a bag."] call ACME_fnc_clinicalNotice;
};

// re-hang a used bag. rebuild the pulled bag on the selected access with its exact remaining volume. the hung-bag
// entry is pushed straight onto IV_Bags, because the flow is derived from IV_Bags, so it hangs and runs from
// where it was left. a used ACME_SalineY keeps that type, so it re-hangs as the clamped y reserve, and onto an
// already-y'd site it simply joins the y. this branch fully owns the used case and never falls through to the
// loose-bag paths below.
if (_fromUsed) exitWith {
    private _usedId=(((_right lbData _idx) splitString "|") param [3,""]);
    if ((missionNamespace getVariable ["ACME_piggybackPending",[]]) isNotEqualTo []) exitWith {
        [_usedId] call ACME_fnc_piggybackStageUsed;
    };
    private _target2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    private _bp2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
    private _iv2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
    private _site2=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
    if (isNull _target2 || {_bp2==""} || {_site2<0}) exitWith {["Select an access site to hang the used bag on.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;};
    if (_target2 getVariable ["ACME_persistenceFrozen",false]) exitWith {};
    private _used=ACE_player getVariable ["ACME_usedBags",[]]; private _ui=_used findIf {(_x param [0,""])==_usedId}; if (_ui<0) exitWith {};
    private _record=+(_used select _ui);
    if ((_record param [9, ""]) isEqualTo "bagOnly" && {_lineContext isEqualTo []}) exitWith {
        [ACE_player,"Select an installed empty IV line for this bag. It has no tubing of its own."] call ACME_fnc_clinicalNotice;
    };
    // Reserve locally before the network round-trip. A rejected owner transaction restores this exact record.
    _used deleteAt _ui; ACE_player setVariable ["ACME_usedBags",_used,true];
    private _requestId=format ["rehang:%1:%2:%3",clientOwner,diag_frameNo,floor(diag_tickTime*1000)];
    private _pending=uiNamespace getVariable ["ACME_usedRehangPending",createHashMap]; _pending set [_requestId,_record]; uiNamespace setVariable ["ACME_usedRehangPending",_pending]; uiNamespace setVariable ["ACME_usedRowSig","__force__"];
    private _contexts = uiNamespace getVariable ["ACME_usedRehangContext",createHashMap];
    _contexts set [_requestId,[ACE_player,_target2,_usedId]];
    uiNamespace setVariable ["ACME_usedRehangContext",_contexts];
    private _warmer=false;
    private _args = [_target2,ACE_player,_bp2,_iv2,_site2,_usedId,_record,[_target2] call ACME_fnc_clinicalEpoch,_requestId,_warmer,serverTime];
    if (_lineContext isNotEqualTo []) then {_args pushBack (_lineContext select 4);};
    [_target2,"rehangUsedBag",_args] call ACME_fnc_ownerDispatch;
};

private _isBlood  = ((toLowerANSI _class) find "blood")  >= 0;
private _isSaline = ((toLowerANSI _class) find "saline") >= 0;
// the kind stored on a staged single-bag set: saline, blood or premixed, where premixed is any other carrier such
// as PlasmaLyte, mannitol, HTS or magnesium. only saline sets can become an infusion, through prep infusion, and
// blood and premixed are grayed.
private _kind = "premixed";
if (_isSaline) then { _kind = "saline"; } else { if (_isBlood) then { _kind = "blood"; }; };

// a blood unit that is mid-y-pairing, armed for a y set, must not be spiked out from under the build.
if (_isBlood && {(missionNamespace getVariable ["ACME_yPending", ""]) == _class}) exitWith {
    ["This blood is armed for a Y set. Finish or clear the Y build first.", 3.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// Draw once, then resume only if the original patient/access selection is live.
if (_isBlood && {_fromCooler} && {_coolerResume isEqualTo []}) exitWith {
    private _context=[_target,missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],if (isNull _target) then {-1} else {[_target] call ACME_fnc_clinicalEpoch},missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0]];
    if (_lineContext isNotEqualTo []) then {_context pushBack (_lineContext select 4);};
    [ACE_player,_class,[ACME_fnc_coolerDrawDone,[_class,_action,_context]]] call ACME_fnc_coolerDraw;
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
    private _warmer = false;
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
    if (([ACE_player, _target, _class] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
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
    if (([ACE_player, _target, _class] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        ["Bag not on hand.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    };
    ["saline"] call _requestYRefill;
};

// A fitted empty line already paid for its tubing. Attach only the selected bag.
private _plainType = getText (configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type");
if (_lineContext isNotEqualTo [] && {_plainType in ["Saline","PlasmaLyte","Plasma","Blood"] || {(_action find "FreshBloodBag_") == 0}}) exitWith {
    [_class, _action, _lineContext select 4, _fromCooler] call ACME_fnc_attachBagToLine;
};

// spike into stage. any bag not caught above is spiked and staged into the prepared iv sets.
private _setItem = "ACME_IVLine";
private _setName = "an IV line (administration set)";
if (([ACE_player, _target, _setItem] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    [format ["You need %1 to spike this bag.", _setName], 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
// The selected fluid source is rechecked atomically at commit.
// do not start a second spike while one is running.
if (count (missionNamespace getVariable ["ACME_spikingActive", []]) > 0) exitWith {};

// a "Spiking Bag..." beat on the button, then the commit, which consumes the iv line and the bag and stores a
// single-bag set.
private _spikeSerial = (missionNamespace getVariable ["ACME_spikeSerial",0]) + 1;
missionNamespace setVariable ["ACME_spikeSerial",_spikeSerial];
private _spikeSession = [_class,diag_tickTime + 1.6,format ["spike:%1:%2",clientOwner,_spikeSerial]];
missionNamespace setVariable ["ACME_spikingActive",_spikeSession];
call ACME_fnc_updateTransfusionControls;
[{
    params ["_class", "_action", "_setItem", "_setName", "_kind", "_cold", "_medic", "_target", "_inventoryMode", "_sourceVehicle", "_piggybackContext", "_spikeSession"];
    if ((missionNamespace getVariable ["ACME_spikingActive",[]]) isNotEqualTo _spikeSession) exitWith {};
    missionNamespace setVariable ["ACME_spikingActive", []];
    if (isNull _medic || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACME_persistenceFrozen",false]}
        || {!isNull _target && {_target getVariable ["ACME_persistenceFrozen",false] || {_medic distance _target > 5}}}) exitWith {};
    private _sameProviderPeriod = _piggybackContext isEqualTo [] || {
        (_medic getVariable ["ACME_equipmentKitEpoch",0]) == (_piggybackContext select 1)
            && {(_medic getVariable ["ACME_providerLocalityEpoch",0]) == (_piggybackContext select 2)}
            && {(missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]) == (_piggybackContext select 3)}
            && {(missionNamespace getVariable ["ACME_piggybackPending",[]]) isEqualTo (_piggybackContext select 0)}
    };
    if (!_sameProviderPeriod) exitWith {};
    if (([_medic, _target, _setItem] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
        [format ["%1 is no longer available.", _setName], 2, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    // Capture inventory choice when clicked; toggling the pane during the short spike beat cannot
    // redirect the debit to another person's bag. Reserve both components, refund if either vanished.
    private _receipts = [];
    isNil {
        private _bagReceipt = [_medic, _target, _class, _inventoryMode, _sourceVehicle] call ACME_fnc_transfusionTakeSelected;
        if (_bagReceipt isNotEqualTo []) then {
            private _setReceipt = [_medic, _target, [_setItem]] call ACME_fnc_treatmentSupplyTake;
            if (_setReceipt isEqualTo []) then {
                [_bagReceipt] call ACME_fnc_treatmentSupplyRefund;
            } else {_receipts = [_bagReceipt, _setReceipt];};
        };
        true
    };
    if (_receipts isEqualTo []) exitWith {
        ["The selected bag or administration set is no longer available.", 2, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    private _cfg = configFile >> "CfgWeapons" >> _class;
    private _nm = [getText (_cfg >> "displayName"), getText (_cfg >> "shortName")] select (isText (_cfg >> "shortName"));
    if (_nm isEqualTo "") then { _nm = _class; };
    private _label = format ["%1%2", _nm, ["", " [Cooled]"] select _cold];

    private _serial = (missionNamespace getVariable ["ACME_preparedItemSerial",0])+1;
missionNamespace setVariable ["ACME_preparedItemSerial",_serial];
private _id = format ["set:%1:%2:%3",clientOwner,netId _medic,_serial];
    private _rec = [_id, _class, _action, "", "", "", _label, _cold, _kind];
    private _setsBefore = +(_medic getVariable ["ACME_preparedIVSets", []]);
    private _sets = +_setsBefore;
    _sets pushBack _rec;
    _medic setVariable ["ACME_preparedIVSets", _sets, true];
    private _committed = [_medic] call ACME_fnc_preparedInventoryCommit;
    if (isNil "_committed" || {!_committed}) exitWith {
        _medic setVariable ["ACME_preparedIVSets",_setsBefore,true];
        {[_x] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
        [_medic,"The bag could not be prepared. Its fluid and IV line were kept."] call ACME_fnc_clinicalNotice;
    };
    {[_x, false] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
    ["Bag spiked. Preparing the IV set.", 2, _medic] call ace_common_fnc_displayTextStructured;
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];


    // A spike creates carried prepared custody, not a hung bag. Refresh the
    // source inventory, then reveal the prepared list without touching Fluids.
    if (!isNull (findDisplay 86000)) then {[false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;};
    [true] call ACME_fnc_togglePreparedSets;
    // A loose secondary needs one real branch line, but no medication admixture.
    // Wait for its native prepared carrier before reserving the exact new set.
    // Changing patient, access, provider period or workflow keeps it carried.
    if (_piggybackContext isNotEqualTo []) then {
        _piggybackContext params ["_intent","_kit","_locality","_workflow"];
        private _valid = {
            params ["_medic","_intent","_id","_kit","_locality","_workflow"];
            private _patient = _intent select 0;
            !isNull _medic && {local _medic} && {alive _medic} && {_medic isEqualTo ACE_player}
                && {(_medic getVariable ["ACME_equipmentKitEpoch",0]) == _kit}
                && {(_medic getVariable ["ACME_providerLocalityEpoch",0]) == _locality}
                && {!(_medic getVariable ["ACME_persistenceFrozen",false])}
                && {!isNull _patient} && {!(_patient getVariable ["ACME_persistenceFrozen",false])}
                && {(_intent select 5) == ([_patient] call ACME_fnc_clinicalEpoch)}
                && {(missionNamespace getVariable ["ACME_piggybackPending",[]]) isEqualTo _intent}
                && {(missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]) == _workflow}
                && {(_intent select [0,4]) isEqualTo [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull],
                    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
                    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
                    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]]}
                && {(((_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [toLowerANSI (_intent select 1),[]]) findIf {
                    (_x param [8,""]) == (_intent select 4) && {(_x param [3,-1]) == (_intent select 3)}
                        && {(_x param [4,true]) isEqualTo (_intent select 2)}
                }) >= 0}
        };
        [
            {params ["_medic","_intent","_id","_kit","_locality","_workflow","_valid"];
                !([_medic,_intent,_id,_kit,_locality,_workflow] call _valid) || {[_medic,"prepared",_id] call ACME_fnc_inventoryLedgerPossessed}},
            {params ["_medic","_intent","_id","_kit","_locality","_workflow","_valid"];
                if ([_medic,_intent,_id,_kit,_locality,_workflow] call _valid && {[_medic,"prepared",_id] call ACME_fnc_inventoryLedgerPossessed}) then {
                    [_id] call ACME_fnc_piggybackAttachRequest;
                };},
            [_medic,_intent,_id,_kit,_locality,_workflow,_valid],10,
            {params ["_medic"];
                if (!isNull _medic && {local _medic}) then {[_medic,"The secondary remains in Prepared IV Sets while its inventory receipt is pending."] call ACME_fnc_clinicalNotice;};}
        ] call CBA_fnc_waitUntilAndExecute;
    };
}, [_class, _action, _setItem, _setName, _kind, (_isBlood && _fromCooler), ACE_player, _target,
    (if (_fromCooler) then {0} else {missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory", 0]}),
    objectParent ACE_player,if (_piggybackIntent isEqualTo []) then {[]} else {[+_piggybackIntent,
        ACE_player getVariable ["ACME_equipmentKitEpoch",0],ACE_player getVariable ["ACME_providerLocalityEpoch",0],
        missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]]},_spikeSession], 1.6] call CBA_fnc_waitAndExecute;
