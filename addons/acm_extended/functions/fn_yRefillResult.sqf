// Provider-side acknowledgement for the owner-authoritative Y refill claim/finalize transaction.
params [
    ["_patient",objNull,[objNull]],
    ["_requestId","",[""]],
    ["_stage","",[""]],
    ["_accepted",false,[false]],
    ["_reason","",[""]]
];
if (!hasInterface || {isNull ACE_player} || {_requestId == ""}) exitWith {};
private _pending = uiNamespace getVariable ["ACME_yRefillPending",createHashMap];
private _ctx = _pending getOrDefault [_requestId,[]];
if (_stage == "claim") then {
    if (_ctx isEqualTo []) exitWith {};
    _ctx params ["_p","_mode","_class","_action","_part","_iv","_site","_epoch","_inventoryMode","_fromCooler","_warmer"];
    if (!_accepted) exitWith {
        _pending deleteAt _requestId; uiNamespace setVariable ["ACME_yRefillPending",_pending];
        if (_reason != "") then {[_reason,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};
    };

    private _cancel = {
        params [["_msg","",[""]]];
        [_p,"yRefill",[_p,ACE_player,"cancel",_requestId,_mode,_part,_iv,_site,_epoch,_fromCooler,_warmer]] call ACME_fnc_ownerDispatch;
        _pending deleteAt _requestId; uiNamespace setVariable ["ACME_yRefillPending",_pending];
        if (_msg != "") then {[_msg,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};
    };
    private _display = findDisplay 86000;
    if (isNull _display || {isNull _p}
        || {!((missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull]) isEqualTo _p)}) exitWith {
        ["Y refill cancelled because the transfusion menu changed."] call _cancel;
    };
    if !([_p,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {
        ["That IV/IO access is no longer available."] call _cancel;
    };

    // Cooler rows are virtual inventory rows. Once drawn out by fn_transfusionSpikeOrAdd the physical unit is on
    // the medic, regardless of whichever inventory pane happened to be selected before the claim round-trip.
    if (_fromCooler) then {_inventoryMode = 0;};
    private _vehicle = objectParent ACE_player;
    private _inventoryTarget = [ACE_player,_p,_vehicle] param [_inventoryMode,ACE_player];
    private _hasItem = if (_inventoryMode == 2) then {
        !isNull _vehicle && {_class in ((getItemCargo _vehicle) select 0)}
    } else {
        !isNull _inventoryTarget && {([_inventoryTarget,_class] call ACME_fnc_itemCount) > 0}
    };
    if (!_hasItem) exitWith {["The selected replacement bag is no longer available."] call _cancel;};

    private _cfg = configFile >> "CfgWeapons" >> _class;
    if ((getNumber (_cfg >> "uniqueBag")) > 0) then {
        private _parts = _class splitString "_";
        private _freshID = parseNumber (_parts param [3,"-1"]);
        private _freshEntry = [_freshID] call ACM_circulation_fnc_getFreshBloodEntry;
        if !(_freshEntry isEqualType [] && {count _freshEntry >= 3}) exitWith {
            ["ACM_circulation_requestFreshBloodRegistry",[ACE_player]] call CBA_fnc_serverEvent;
            ["Donor blood bag data is still synchronizing. Reopen the transfusion menu in a moment."] call _cancel;
        };
    };

    missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",_part];
    missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",_iv];
    missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",_site];
    missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",_inventoryMode];

    private _right = _display displayCtrl 86005;
    private _row = -1;
    for "_i" from 0 to ((lbSize _right)-1) do {
        private _d = (_right lbData _i) splitString "|";
        if ((_d param [0,""]) == _class && {(_d param [1,""]) == _action}) exitWith {_row = _i;};
    };
    if (_row < 0) then {
        // The inventory list can rebuild during the claim round-trip. A temporary row only carries the exact class
        // and ACM fluid action; native Add Bag still validates and consumes from the captured inventory mode.
        _row = _right lbAdd (getText (_cfg >> "displayName"));
        _right lbSetData [_row,format ["%1|%2",_class,_action]];
    };
    _right lbSetCurSel _row;
    uiNamespace setVariable ["ACME_yRefillActive",[_p,_requestId,_mode,_part,_iv,_site,_epoch,_fromCooler,_warmer,_class,_action]];
    call ACM_circulation_fnc_TransfusionMenu_AddBag;
};

if (_stage == "cancel") exitWith {
    if !(_ctx isEqualTo []) then {_pending deleteAt _requestId; uiNamespace setVariable ["ACME_yRefillPending",_pending];};
};
if (_stage == "done") exitWith {
    if !(_ctx isEqualTo []) then {
        _ctx params ["_p","_mode","_class","_action","_part","_iv","_site","_epoch","_inventoryMode","_fromCooler","_warmer"];
        _pending deleteAt _requestId; uiNamespace setVariable ["ACME_yRefillPending",_pending];
        if (_accepted) then {
            if (_mode == "saline") then {
                ["Y saline reserve replaced.",2.5,ACE_player] call ace_common_fnc_displayTextStructured;
            } else {
                if (_warmer) then {["Blood warmer inline.",2,ACE_player] call ace_common_fnc_displayTextStructured;};
                if (_fromCooler && {!_warmer}) then {["Cold blood hung. Use the warmer.",2,ACE_player] call ace_common_fnc_displayTextStructured;};
            };
        } else {
            if (_reason != "") then {[_reason,3,ACE_player,13] call ace_common_fnc_displayTextStructured;};
        };
    };
    uiNamespace setVariable ["ACME_coolerRowSig","__force__"];
    if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList" && {!isNull (findDisplay 86000)}) then {[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;};
};
