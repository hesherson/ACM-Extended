/* Reuse exactly the native list's card model and viewport. No second access chooser or raw patient dump. */
params ["_display"];
private _context = _display getVariable ["ACME_reactContext",[]];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {createHashMap};
private _list = _display displayCtrl 86004;
private _layout = (_display getVariable ["ACME_txCardLayout",createHashMap]) getOrDefault [86004,[]];
if (isNull _list || {count _layout != 5}) exitWith {createHashMap};
private _offset = _layout select 3;
private _window = [lbSize _list,2,_offset] call ACME_fnc_transfusionCardWindow;
private _identities = (_window select 1) apply {if (_x < 0) then {[]} else {[_list,_x] call ACME_fnc_transfusionCardIdentity}};
private _route = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]];
private _binding = str [_route,_identities];
if (_binding != (_display getVariable ["ACME_reactRowBinding",""])) then {
    _display setVariable ["ACME_reactRowBinding",_binding];
    _display setVariable ["ACME_reactRowRevision",(_display getVariable ["ACME_reactRowRevision",0]) + 1];
};
private _revision = _display getVariable ["ACME_reactRowRevision",0];
private _rows = createHashMap;
private _cards = [];
{
    private _slot = _forEachIndex;
    private _row = _x;
    private _identity = _identities select _slot;
    if (_row >= 0 && {_identity isNotEqualTo []}) then {
        private _data = [_list,_row] call ACME_fnc_transfusionCardData;
        _data params ["_name","_detail","_status","_thermal","_color","_icon","_vial","_fraction","_total"];
        if (_name != "") then {
            private _token = format ["row:%1:%2",_revision,_slot];
            _rows set [_token,_identity];
            _cards pushBack createHashMapFromArray [
                ["slot",_slot],["token",_token],["name",_name select [0,512]],
                ["detail",_detail select [0,1024]],["status",_status select [0,128]],["thermal",_thermal select [0,128]],
                ["color",_color],["icon",_icon select [0,512]],["vial",_vial select [0,512]],
                ["fraction",_fraction],["marks",[_total] call ACME_fnc_transfusionGraduations],
                ["selected",(lbCurSel _list) == _row]
            ];
        };
    };
} forEach (_window select 1);
_display setVariable ["ACME_reactRows",_rows];
createHashMapFromArray [
    ["view","transfusion-cards"],["patient",createHashMapFromArray [
        ["ref",["encode",_context select 1] call ACME_fnc_clinicalObjectRef],["epoch",_context select 4]]],
    ["cards",_cards],["canPrevious",_window select 2],["canNext",_window select 3]
]
