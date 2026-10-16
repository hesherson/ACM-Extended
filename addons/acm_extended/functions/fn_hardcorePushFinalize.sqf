/* B121: settle the active syringe after completion or an intentional/safety stop. This is the only place a
   physical partial syringe is returned to inventory. */
private _retiredJob = if (!isNil "_this" && {_this isEqualType []} && {count _this == 1}
    && {(_this select 0) isEqualType createHashMap}) then {_this select 0} else {createHashMap};
private _detached = count _retiredJob > 0;
private _job = if (_detached) then {_retiredJob} else {missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap]};
if !(_job isEqualType createHashMap && {count _job > 0}) exitWith {false};
if ((_job getOrDefault ["pendingAcks",0]) > 0) exitWith {false};
private _unsent = _job getOrDefault ["unsentDelta",[0,0,[]]];
if ((_unsent param [0,0]) + (_unsent param [1,0]) > 0.000001) exitWith {false};
private _medic = _job getOrDefault ["medic",objNull];
private _stable = _job getOrDefault ["stableId",""];
private _completed = (_job getOrDefault ["stopReason",""]) == "complete";
private _pushLabel = _job getOrDefault ["pushLabel",_job getOrDefault ["med","Medication"]];
if (_pushLabel == "") then {_pushLabel = "Medication";};
if (isNull _medic || {!local _medic}) exitWith {false};
private _journal = _job getOrDefault ["syringeDelivery",false];
private _store = +(_medic getVariable ["ACME_narcStore",[]]);
private _idx = _store findIf {(_x param [11,"",[""]]) == _stable};
private _keepRow = _idx >= 0;
if (!_journal && {_keepRow}) then {
    private _row = +(_store select _idx);
    private _total = ((_row param [2,0,[0]]) + (_row param [4,0,[0]])) max 0;
    if (_total <= 0.0005) then {_store deleteAt _idx; _keepRow = false;} else {
        if (!(_job getOrDefault ["virtual",false]) && {!(_job getOrDefault ["inventoryBacked",false])}) then {
            // Physical syringe magazines store 0.01 mL quanta. Keep the row and magazine exactly synchronized.
            private _ammo = round ((_row param [2,0,[0]]) * 100);
            _row set [2,_ammo / 100];
            _store set [_idx,_row];
            if (_ammo > 0) then {
                private _container = _job getOrDefault ["magContainer",objNull];
                private _magClass = _job getOrDefault ["magClass",""];
                if (_magClass != "") then {
                    if (!isNull _container) then {_container addMagazineAmmoCargo [_magClass,1,_ammo];}
                    else {_medic addMagazine [_magClass,_ammo];};
                };
            };
        } else {_store set [_idx,_row];};
    };
};
if (!_journal) then {[_medic,_store] call ACME_fnc_narcStoreCommit;};
if (!_journal && {_job getOrDefault ["inventoryBacked",false]}) then {
    [_medic,_job getOrDefault ["inventoryRequest",""],_stable] call ACME_fnc_skInventorySettle;
};
// A stopped, captured archive settles inventory only. It cannot clear another
// provider's active job, UI controls or numeric CBA handler.
if (_detached) exitWith {true};
missionNamespace setVariable ["ACME_HCMedPushJob",createHashMap];
uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
private _h = missionNamespace getVariable ["ACME_HCMedPushPFH",-1];
if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler;};
missionNamespace setVariable ["ACME_HCMedPushPFH",-1];
["clear"] call ACME_fnc_hardcorePushOverlay;
if (_completed) then {
    [format ["%1 pushed successfully.",_pushLabel],3,_medic] call ace_common_fnc_displayTextStructured;
};
if (!isNull (findDisplay 84000)) then {
    private _d = findDisplay 84000;
    {private _c=_d displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true;};} forEach [84150,84151,84154,84470,84831];
    if (_keepRow) then {[_stable,[ACE_player] call ACME_fnc_skStoreEnsureIds] call ACME_fnc_skSelectStored;};
    call ACME_fnc_skRefreshDrawn;
    [0] call ACME_fnc_skCarouselRender;
    call ACME_fnc_skBuildHotspots;
    call ACME_fnc_skBodyActionRender;
};
// All local controller/UI teardown precedes a potentially synchronous ready
// reply. Only that server row can release the prepared carrier.
if (_journal) then {
    ["stop",_medic,_job getOrDefault ["inventoryRequest",""],[_job getOrDefault ["session",""],_job getOrDefault ["stopReason","stopped"]]] call ACME_fnc_syringeDeliveryRequest;
};
true
