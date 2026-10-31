/* B13: render-frame input -> bounded heartbeat. No provider writes patient physiology. */
disableSerialization;
params [["_force", false], ["_closing", false]];
private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
private _patient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _medic = uiNamespace getVariable ["ACME_laryngo_medic", objNull];
private _token = uiNamespace getVariable ["ACME_suctionToken", ""];
if (isNull _patient || {isNull _medic} || {!local _medic} || {_token == ""}) exitWith {};
private _epoch = uiNamespace getVariable ["ACME_suctionEpoch", -1];
private _sameLife = _epoch == ([_patient] call ACME_fnc_clinicalEpoch);
private _mode = "off";
private _type = uiNamespace getVariable ["ACME_suction_type", -1];
private _pin = uiNamespace getVariable ["ACME_laryngo_sucPinned", false];
private _holding = (uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction";
private _inMouth = uiNamespace getVariable ["ACME_laryngo_sucInMouth", false];
private _valid = _sameLife && {!isNull _dlg} && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {_medic distance _patient <= 5 || {!isNull objectParent _medic && {objectParent _medic == objectParent _patient}}};
if (_valid && {_inMouth}) then {
    if (_type == 1 && {(_pin || _holding)} && {uiNamespace getVariable ["ACME_laryngo_sucOn", false]}) then {_mode = if (_pin) then {"salad"} else {"hand"};};
    if (_type == 0 && {_holding} && {(uiNamespace getVariable ["ACME_suction_sqT0", -1]) >= 0}) then {_mode = "manual";};
};
if (_closing) then {_mode = "closed";};
if (_type < 0 || {!_valid}) then {
    uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
    uiNamespace setVariable ["ACME_laryngo_sucOn", false];
    [_medic] call ACME_fnc_suctionSfxStop;
};
private _now = CBA_missionTime;
private _changed = _mode != (uiNamespace getVariable ["ACME_suctionLastMode", ""]);
if (!_force && {!_changed} && {_now < (uiNamespace getVariable ["ACME_suctionNextPublish", 0])}) exitWith {};
uiNamespace setVariable ["ACME_suctionNextPublish", _now + 0.25];
uiNamespace setVariable ["ACME_suctionLastMode", _mode];
private _seq = (uiNamespace getVariable ["ACME_suctionPublishSeq", 0]) + 1;
uiNamespace setVariable ["ACME_suctionPublishSeq", _seq];
(uiNamespace getVariable ["ACME_laryngo_frame", [0,0,1,1]]) params ["_fx","_fy","_fw","_fh"];
(uiNamespace getVariable ["ACME_laryngo_cur", [0,0]]) params ["_cx","_cy"];
(uiNamespace getVariable ["ACME_Laryngo_ShakeBase_off", [0,0]]) params ["_dx","_dy"];
private _position = if (_pin) then {uiNamespace getVariable ["ACME_laryngo_sucPinRel", []]} else {[(_cx - _fx - _dx) / (_fw max 0.00001), (_cy - _fy - _dy) / (_fh max 0.00001)]};
[_patient, "suctionState", [_patient, _medic, _epoch, _token, _seq, _mode, _position, _type]] call ACME_fnc_ownerDispatch;
private _totals = (_patient getVariable ["ACME_suctionTotals", []]) select {(_x select 0) == _token};
if !(_totals isEqualTo []) then {
    uiNamespace setVariable ["ACME_suction_totalMl", (uiNamespace getVariable ["ACME_suctionTotalBase", 0]) + ((_totals select 0) select 1)];
    uiNamespace setVariable ["ACME_suction_bagMl", (uiNamespace getVariable ["ACME_suctionBagBase", 0]) + ((_totals select 0) select 2)];
};
