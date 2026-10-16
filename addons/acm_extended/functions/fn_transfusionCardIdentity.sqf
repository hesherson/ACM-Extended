/* B276: a card binds physical/staged custody identity, never a transient visible row number. */
params ["_list","_row"];
if (isNull _list || {_row < 0} || {_row >= lbSize _list}) exitWith {[]};
private _idc = ctrlIDC _list;
private _value = _list lbValue _row;
if (_idc in [86004,86129,86127] && {_value < 0}) exitWith {[]};
if (_idc in [86004,86129]) exitWith {
    private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[]];
    private _bag = _selection param [_value,[]];
    if (_bag isEqualTo []) exitWith {[]};
    private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
    private _immutable = [_bag param [0,""],_bag param [2,0],_bag param [3,-1],_bag param [4,false],_bag param [5,-1],_bag param [6,0],_bag param [7,-1]];
    ["active",_part,_bag param [4,false],_bag param [3,-1],_bag param [9,""],if ((_bag param [9,""]) == "") then {_immutable} else {[]}]
};
if (_idc == 86127) exitWith {
    private _entry = (ACE_player getVariable ["ACME_infusion_PreparedBags",[]]) param [_value,[]];
    if (_value < 0 || {_entry isEqualTo []}) exitWith {[]};
    ["prepared",_entry param [0,""]]
};
private _data = _list lbData _row;
if (_data == "") exitWith {[]};
[["inventory","set"] select (_idc == 86145),_data]
