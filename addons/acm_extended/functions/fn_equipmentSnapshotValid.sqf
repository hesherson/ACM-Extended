/* Pure schema validation for personal virtual stores and removed-carrier custody. */
params ["_snapshot"];
if (isNil "_snapshot") exitWith {false};
if !(_snapshot isEqualType [] && {count _snapshot in [5,6]}) exitWith {false};
if (([0,1,2,3,4] findIf {isNil {_snapshot select _x}}) >= 0) exitWith {false};
_snapshot params ["_version","_vials","_bags","_vent","_carrier"];
if (_version isNotEqualTo 1) exitWith {false};
if (([_vials,_bags,_vent,_carrier] findIf {!(_x isEqualType []) || {count _x > 1024}}) >= 0) exitWith {false};
private _seen = createHashMap;
private _ok = true;
{
    if !(_x isEqualType [] && {count _x == 2}) exitWith {_ok = false;};
    if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_ok = false;};
    _x params ["_med","_ml"];
    if !(_med isEqualType "" && {count _med > 0} && {count _med <= 128} && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0} && {_ml <= 1e6}) exitWith {_ok = false;};
    if (_med in _seen || {([_med] call ACME_fnc_vialCapacity) <= 0}) exitWith {_ok = false;};
    _seen set [_med,true];
} forEach _vials;
if (!_ok) exitWith {false};
_seen = createHashMap;
{
    if !(_x isEqualType [] && {count _x in [7,8,9]}) exitWith {_ok = false;};
    private _row = _x;
    if (([0,1,2,3,4,5,6] findIf {isNil {_row select _x}}) >= 0) exitWith {_ok = false;};
    _x params ["_id","_type","_ml","_access","_blood","_original","_name",["_fresh",-1]];
    if !(_id isEqualType "" && {count _id > 0} && {count _id <= 256} && {_type isEqualType ""} && {count _type > 0} && {count _type <= 128}
        && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0} && {_original isEqualType 0} && {finite _original} && {_original > 0} && {_original <= 1e6} && {_ml <= _original}
        && {_access isEqualType 0} && {finite _access} && {_access == floor _access} && {_access >= 0} && {_access <= 32} && {_blood isEqualType 0} && {finite _blood} && {_blood == floor _blood} && {_blood >= -1} && {_blood <= 16}
        && {_name isEqualType ""} && {count _name <= 256} && {_fresh isEqualType 0} && {finite _fresh} && {_fresh == floor _fresh} && {_fresh >= -1}) exitWith {_ok = false;};
    if (_type == "FreshBlood") then {
        if !(_blood in [0,1,2,3,4,5,6,7]) exitWith {_ok = false;};
        private _meta = _row param [8,[]];
        if (_meta isNotEqualTo ["freshMissingV1"]) then {
        if !(_meta isEqualType [] && {count _meta == 4}) exitWith {_ok = false;};
        if (([0,1,2,3] findIf {isNil {_meta select _x}}) >= 0) exitWith {_ok = false;};
        if ((_meta select 0) isNotEqualTo "freshAgeV1" || {!((_meta select 1) isEqualType false)}
            || {!((_meta select 2) isEqualType 0)} || {!finite (_meta select 2)} || {(_meta select 2) < 0} || {(_meta select 2) > 1e9}
            || {(_meta select 3) isNotEqualTo _blood}) exitWith {_ok = false;};
        };
    };
    if (!_ok) exitWith {};
    if (_id in _seen) exitWith {_ok = false;};
    _seen set [_id,true];
} forEach _bags;
if (!_ok) exitWith {false};
_seen = createHashMap;
private _fields = [] call ACME_fnc_ventDeviceFields;
{
    if !(_x isEqualType [] && {count _x == 2}) exitWith {_ok = false;};
    if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_ok = false;};
    _x params ["_field","_value"];
    if !(_field isEqualType "" && {_field in _fields} && {!(_field in _seen)}) exitWith {_ok = false;};
    private _valid = if (_field in ["ACME_vent_mode","ACME_vent_iface"]) then {_value isEqualType "" && {count _value <= 64}} else {
        if (_field == "ACME_vent_alertInvIE") then {_value isEqualType false} else {_value isEqualType 0 && {finite _value} && {abs _value <= 1e6}}
    };
    if (_field == "ACME_vent_battery" && {_valid}) then {_valid = _value >= 0 && {_value <= 100};};
    if (!_valid) exitWith {_ok = false;};
    _seen set [_field,true];
} forEach _vent;
if (!_ok) exitWith {false};
private _carrierValid = {
    params ["_carrier"];
    if (_carrier isEqualTo []) exitWith {true};
    if (count _carrier != 3) exitWith {false};
    if (([0,1,2] findIf {isNil {_carrier select _x}}) >= 0) exitWith {false};
    _carrier params ["_savedVar","_vest","_tree"];
    _savedVar in ["ACME_chestAccess_vestLoadout","ACME_CS_vestLoadout","ACME_headElev_vestLoadout"]
        && {_vest isEqualType ""} && {count _vest > 0} && {count _vest <= 256}
        && {isClass (configFile >> "CfgWeapons" >> _vest)} && {[_tree] call ACME_fnc_equipmentCargoValid}
};
if !([_carrier] call _carrierValid) exitWith {false};
if (count _snapshot == 5) exitWith {true};
if (isNil {_snapshot select 5}) exitWith {false};
private _nested = _snapshot select 5;
if !(_nested isEqualType [] && {count _nested <= 192}) exitWith {false};
{
    if !(_x isEqualType [] && {count _x == 3}) exitWith {_ok = false;};
    private _entry = _x;
    if (([0,1,2] findIf {isNil {_entry select _x}}) >= 0) exitWith {_ok = false;};
    _entry params ["_slot","_class","_tree"];
    if !(_slot in [0,1,2] && {_class isEqualType ""} && {_class != ""} && {count _class <= 256}
        && {[_tree] call ACME_fnc_equipmentCargoValid}) exitWith {_ok = false;};
} forEach _nested;
_ok
