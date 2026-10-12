/* Native card input resolves current custody identity, then delegates to the unchanged list selection handler. */
disableSerialization;
params ["_hit",["_operation","select"],["_argument",0]];
private _display = ctrlParent _hit;
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {true};
private _idc = _hit getVariable ["ACME_txListIDC",-1];
private _list = _display displayCtrl _idc;
if (isNull _list) exitWith {true};
private _offsetKey = format ["ACME_txCardOffset_%1",_idc];
private _capacity = _hit getVariable ["ACME_txCapacity",2];
if (_operation == "wheel") exitWith {
    private _offset = _display getVariable [_offsetKey,0];
    _display setVariable [_offsetKey,(_offset - (if (_argument > 0) then {1} else {-1})) max 0];
    [_display] call ACME_fnc_updateTransfusionCards;
    true
};
private _row = -1;
if (_operation == "key") then {
    private _selected = lbCurSel _list;
    _row = switch (_argument) do {
        case 200: {(_selected - 1) max 0};
        case 208: {(_selected + 1) min ((lbSize _list) - 1)};
        case 201: {(_selected - _capacity) max 0};
        case 209: {(_selected + _capacity) min ((lbSize _list) - 1)};
        case 199: {0};
        case 207: {(lbSize _list) - 1};
        default {-1};
    };
    if (_row >= 0) then {
        private _window = [lbSize _list,_capacity,_display getVariable [_offsetKey,0],_row,true] call ACME_fnc_transfusionCardWindow;
        _display setVariable [_offsetKey,_window select 0];
    };
} else {
    private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    if ((_hit getVariable ["ACME_txPatient",objNull]) isNotEqualTo _patient) exitWith {};
    _row = [_list,_hit getVariable ["ACME_txIdentity",[]]] call ACME_fnc_transfusionCardResolve;
};
if (_row < 0) exitWith {[_display] call ACME_fnc_updateTransfusionCards;_operation != "key"};
private _identity = [_list,_row] call ACME_fnc_transfusionCardIdentity;
if (_identity isEqualTo []) exitWith {true};
if ((_identity select 0) == "active") then {
    // A replication delay may leave the original list behind physical custody. Never accept that removed UID.
    private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    private _physical = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_identity select 1,[]];
    private _uid = _identity select 4;
    if (_uid != "" && {(_physical findIf {(_x param [8,""]) == _uid && {(_x param [3,-1]) == (_identity select 3)} && {(_x param [4,false]) isEqualTo (_identity select 2)}}) < 0}) then {_row = -1;};
};
if (_row < 0) exitWith {true};
private _pane = switch (_idc) do {case 86129:{"infusion"};case 86004:{"transfusion"};default {"inventory"};};
_display setVariable ["ACME_txActivePane",_pane];
_list lbSetCurSel _row;
if (_idc == 86127) then {_display setVariable ["ACME_txPreparedIdentity",_identity];};
if (_idc == 86145) then {_display setVariable ["ACME_txSetIdentity",_identity];};
if (_idc in [86004,86129]) then {_display setVariable [format ["ACME_txSelectedIdentity_%1",_idc],_identity];};
call ACME_fnc_updateTransfusionControls;
true
