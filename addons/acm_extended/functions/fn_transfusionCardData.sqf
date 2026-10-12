/* B277 read-only card view model. Medical artwork, labels and selection values remain owned by native lists. */
params ["_list","_row"];
private _name = _list lbText _row;
private _detail = "";
private _status = "";
private _thermal = "";
private _color = _list lbColor _row;
private _icon = _list lbPicture _row;
private _vial = _list lbPictureRight _row;
private _fraction = -1;
private _idc = ctrlIDC _list;
if (_idc in [86004,86129]) then {
    private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
    private _selected = (missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[]]) param [_list lbValue _row,[]];
    private _uid = _selected param [9,""];
    private _currentIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
    private _currentSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
    private _quiet = {_name="";_detail="";_status="";_thermal="";_color=[0.66,0.66,0.66,1];_icon="";_vial="";_fraction=-1;};
    if (_selected isEqualTo [] || {(_selected param [4,false]) isNotEqualTo _currentIV} || {(_selected param [3,-1]) != _currentSite}) exitWith {call _quiet;};
    private _physical = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
    private _at = _physical findIf {(_x param [8,""]) == _uid && {_uid != ""}};
    if (_uid != "" && {_at < 0}) exitWith {call _quiet;};
    private _bag = if (_at >= 0) then {+(_physical select _at)} else {_selected select [0,8]};
    if ((_bag param [4,false]) isNotEqualTo _currentIV || {(_bag param [3,-1]) != _currentSite}) exitWith {call _quiet;};
    _bag set [8,_uid];
    ([_patient,_part,_bag] call ACME_fnc_transfusionBagPresentation) params ["_label","_temperatureColor","_lineThermal","_role","_flowing"];
    _name = _label;
    _color = _temperatureColor;
    _thermal = _lineThermal;
    private _remaining = (_bag param [1,0]) max 0;
    private _total = (_bag param [6,0]) max 1;
    _fraction = (_remaining / _total) max 0 min 1;
    _detail = format ["%1 / %2 mL",round _remaining,round _total];
    _status = if (_flowing) then {"Running"} else {"Paused"};
    private _volumeStart = _name find " (";
    if (_volumeStart >= 0) then {
        private _suffix = "";
        if ((_label find "[Y]") >= 0) then {_suffix = " [Y]";};
        if (_role != "") then {_suffix = " [PiB]";};
        _name = (_name select [0,_volumeStart]) + _suffix;
    };
    if (_role != "") then {_status = format ["Piggyback %1",_role];};
    private _all = _patient getVariable ["ACME_infusion_BagMedications",[]];
    private _meds = _all select {(_x param [23,""]) == _uid && {_uid != ""}};
    if (_meds isNotEqualTo []) then {
        private _names = _meds apply {[_x param [11,""]] call ACME_fnc_infusionName};
        _name = (_names arrayIntersect _names) joinString " + ";
        if (_role != "") then {_name = _name + " [PiB]";};
        if ((_label find "[Y]") >= 0) then {_name = _name + " [Y]";};
        private _doses = _meds apply {format ["%1 remaining",[_x param [11,""],_x param [14,0]] call ACME_fnc_formatDose]};
        _detail = format ["%1 mL · %2",round _remaining,_doses joinString " + "];
        if (_vial == "") then {_vial = getText (configFile >> "CfgWeapons" >> ([(_meds select 0) param [11,""]] call ACME_fnc_vialClass) >> "picture");};
    };
    private _isY = [_patient,_part,_bag param [4,true],_bag param [3,-1]] call ACME_fnc_isYLineAccess;
    if (_isY && {(_bag param [0,""]) in ["Saline","ACME_SalineY","ACME_EmptySaline"]}) then {
        _status = "Reserve";
        if (_thermal == "") then {_thermal = "Reserve Flush Saline";};
    };
} else {
    private _cut = _name find " | ";
    if (_cut >= 0) then {_detail = _name select [_cut + 3];_name = _name select [0,_cut];};
    if (_idc == 86145) then {
        private _setId = _list lbData _row;
        private _sets = ACE_player getVariable ["ACME_preparedIVSets",[]];
        private _at = _sets findIf {(_x param [0,""]) == _setId};
        if (_at >= 0) then {
            private _set = _sets select _at;
            _icon = getText (configFile >> "CfgWeapons" >> (_set param [1,""]) >> "picture");
            _detail = if (_detail == "") then {"IV line fitted"} else {_detail};
            _status = "Prepared";
        };
    };
    if (_idc == 86127) then {
        private _entry = (ACE_player getVariable ["ACME_infusion_PreparedBags",[]]) param [_list lbValue _row,[]];
        _icon = getText (configFile >> "CfgWeapons" >> (_entry param [1,""]) >> "picture");
        _vial = getText (configFile >> "CfgWeapons" >> ([_entry param [3,""]] call ACME_fnc_vialClass) >> "picture");
        _status = "Prepared";
    };
};
[_name,_detail,_status,_thermal,_color,_icon,_vial,_fraction]
