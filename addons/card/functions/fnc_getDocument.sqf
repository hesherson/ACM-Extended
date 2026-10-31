/* One replicated aggregate is canonical. Legacy public maps are mirrors only;
 * they are migrated once when an old mission has no aggregate. */
params ["_patient", ["_publish", false]];
if (isNull _patient) exitWith {[]};
private _names = ["DD1380_Priority", "DD1380_Checkboxes", "DD1380_Text", "DD1380_Back_Checkboxes", "DD1380_Back_Text"];
private _document = _patient getVariable ["DD1380_Document", []];
if (isNil "_document") then {_document = [];};
private _canonical = _document isEqualType [] && {count _document == 2}
    && {(_document select 0) isEqualType 0} && {finite (_document select 0)}
    && {(_document select 0) >= 0} && {(_document select 0) == floor (_document select 0)}
    && {(_document select 1) isEqualType []} && {count (_document select 1) == 5}
    && {(_document select 1) isEqualTypeAll createHashMap};
private _revision = if (_canonical) then {_document select 0} else {_patient getVariable ["DD1380_Revision", 0]};
if !(_revision isEqualType 0 && {finite _revision} && {_revision >= 0} && {_revision == floor _revision}) then {_revision = 0;};
private _fields = call DD1380_card_fnc_fieldIds;
private _data = [];
{
    private _index = _forEachIndex;
    private _stored = if (_canonical) then {(_document select 1) select _index} else {_patient getVariable [_x, createHashMap]};
    if !(_stored isEqualType createHashMap) then {_stored = createHashMap;};
    private _default = if (_index in [0, 1, 3]) then {false} else {""};
    private _map = createHashMap;
    {
        private _value = _stored getOrDefault [_x, _default];
        if !(_value isEqualType _default) then {_value = _default;};
        private _limit = if (_x == 1651) then {4096} else {1024};
        if (_value isEqualType "" && {count _value > _limit}) then {_value = _value select [0, _limit];};
        _map set [_x, _value];
    } forEach (_fields select _index);
    _data pushBack _map;
} forEach _names;
_document = [_revision, _data];
if (_publish && {local _patient}) then {
    _patient setVariable ["DD1380_Document", _document, true];
    {_patient setVariable [_x, _data select _forEachIndex, true];} forEach _names;
    _patient setVariable ["DD1380_Revision", _revision, true];
};
_document
