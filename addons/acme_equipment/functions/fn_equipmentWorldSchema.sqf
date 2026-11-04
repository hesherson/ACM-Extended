/* Portable data only. Do not accept arbitrary classes, variables, scripts or live handles. */
params ["_save"];
if !(_save isEqualType [] && {count _save == 2} && {(_save select 0) in [1,2]}
    && {(_save select 1) isEqualType []} && {count (_save select 1) <= 4096}) exitWith {false};
private _refValid = {
    params ["_ref"];
    _ref isEqualType [] && {count _ref == 3} && {_ref isEqualTypeAll ""}
        && {count (_ref select 0) <= 128} && {count (_ref select 1) <= 256} && {count (_ref select 2) <= 256}
        && {(_ref select 2) != "" || {_ref isEqualTo ["0:0","",""]}}
};
private _vectorValid = {params ["_v"]; _v isEqualType [] && {count _v == 3} && {_v isEqualTypeAll 0} && {(_v findIf {!finite _x || {abs _x > 1e7}}) < 0}};
private _ids = []; private _slots = []; private _ok = true;private _mounts=[];private _usbPorts=[];
private _version=_save select 0;
{
    if !(_x isEqualType [] && {count _x == ([10,12] select (_version==2))}) exitWith {_ok = false;};
    _x params ["_id","_kind","_pos","_dir","_up","_manual","_patient","_state","_link","_custody"];
    if !(_id isEqualType "" && {_id != ""} && {count _id <= 256} && {!(_id in _ids)}
        && {_kind in ["pro","ls","accu","vent"]} && {_manual isEqualType false}
        && {[_pos] call _vectorValid} && {[_dir] call _vectorValid} && {[_up] call _vectorValid}
        && {abs (vectorMagnitude _dir - 1) < 0.01} && {abs (vectorMagnitude _up - 1) < 0.01}
        && {abs (_dir vectorDotProduct _up) < 0.01}
        && {[_patient] call _refValid} && {[_link] call _refValid}
        && {_state isEqualType []} && {count _state == 4} && {(_state select 0) isEqualType false}
        && {(_state select 1) isEqualType []} && {count (_state select 1) == 5} && {(_state select 1) isEqualTypeAll false}
        && {(_state select 2) isEqualType false} && {(_state select 3) isEqualType false}
        && {_custody isEqualType []}) exitWith {_ok = false;};
    _ids pushBack _id;
    if ((_patient select 2) != "") then {
        private _slot = [_patient select 2,_kind];
        if (_slot in _slots) exitWith {_ok = false;};
        _slots pushBack _slot;
    };
    if (_kind == "vent") then {
        if (count _custody != 5 || {(_patient select 2) == ""} || {_manual}
            || {!([_custody select 0] call _refValid)} || {!((_custody select 1) isEqualType "")}
            || {count (_custody select 1) > 128} || {!([_custody select 2] call _refValid)}
            || {!([_custody select 3] call _refValid)} || {!((_custody select 4) isEqualType "")}
            || {count (_custody select 4) > 128}) then {_ok = false;};
    } else {if (_custody isNotEqualTo []) then {_ok = false;};};
    if (_kind != "ls" && {_link isNotEqualTo ["0:0","",""]}) then {_ok = false;};
    if (_version==2) then {
        private _mount=_x select 10;private _usb=_x select 11;
        if (!([_mount] call _refValid) || {!([_usb] call _refValid)}) exitWith {_ok=false;};
        private _mountId=_mount select 2;private _usbId=_usb select 2;
        if (_mountId!="") then {
            if (!(_kind in ["pro","ls"]) || {_mountId in _mounts} || {_mountId==_id}) then {_ok=false;};
            _mounts pushBack _mountId;
        };
        if (_usbId!="") then {
            if (_kind!="ls" || {_usbId in _usbPorts} || {_usbId==_id}
                || {(_link select 2)!="" && {(_link select 2)!=_usbId}}) then {_ok=false;};
            _usbPorts pushBack _usbId;
        };
    };
    if (!_ok) exitWith {};
} forEach (_save select 1);
_ok
