/* onUnload owns exactly one page harvest. Its subject, epoch and revision
 * belong to the display, not ACE's currently selected medical-menu target. */
private _acmeReconcile = "B291:DD1380CapturedDocument";
params ["_display"];
if (_display getVariable ["DD1380_closed", false]) exitWith {false};
_display setVariable ["DD1380_closed", true];
private _context = _display getVariable ["DD1380_context", []];
if (count _context != 7) exitWith {false};
_context params ["_medic", "_patient", "_epoch", "_id", "_revision", "_baseline", "_draft"];
private _page = _display getVariable ["DD1380_page", 0];
if (isNull _patient || {!(_page in [1, 2])}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {false};
private _fields = call DD1380_card_fnc_fieldIds;
_draft = +_draft;
{
    private _index = _x;
    private _map = createHashMap;
    {
        _map set [_x, if (_index in [0, 1, 3]) then {cbChecked (_display displayCtrl _x)} else {ctrlText (_display displayCtrl _x)}];
    } forEach (_fields select _index);
    _draft set [_index, _map];
} forEach (if (_page == 1) then {[0, 1, 2]} else {[0, 3, 4]});
_context = [_medic, _patient, _epoch, _id, _revision, _baseline, _draft];
private _current = uiNamespace getVariable ["DD1380_context", []];
private _ownsContext = count _current == 7 && {(_current select 3) isEqualTo _id};
if (_display getVariable ["DD1380_flipping", false]) exitWith {
    if (_ownsContext) then {uiNamespace setVariable ["DD1380_context", _context];};
    true
};
if (_ownsContext) then {
    uiNamespace setVariable ["DD1380_context", nil];
    uiNamespace setVariable ["TCCC_Card", nil];
};
if (_draft isEqualTo _baseline) exitWith {true};
[_medic, [_patient, _medic, _epoch, _id, _revision, _draft, 0]] call DD1380_card_fnc_sendData;
true
