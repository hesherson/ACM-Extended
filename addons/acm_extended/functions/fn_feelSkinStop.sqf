/* Retire this exact tactile exam before touching animation. A delayed stop cannot cancel a successor. */
params [["_medic", objNull], ["_serial", -1], ["_success", false]];
if (isNull _medic) exitWith {};
private _record = _medic getVariable ["ACME_feelSkinAction", []];
if (_record isEqualTo [] || {_serial >= 0 && {(_record select 0) != _serial}}) exitWith {};
_medic setVariable ["ACME_feelSkinAction", []];
if ((_record select 6) >= 0) then {[_record select 6] call CBA_fnc_removePerFrameHandler;};
private _display = _record select 8;
if (!isNull _display) then {
    {_display displayRemoveEventHandler _x;} forEach (_record select 9);
    if ((_display getVariable ["ACME_feelSkinInput", []]) isEqualTo [_medic, _record select 0]) then {
        _display setVariable ["ACME_feelSkinInput", nil];
    };
};
private _epoch = _record select 2;
if (_epoch >= 0) then {[_medic, "", _epoch] call ACME_fnc_treatmentPoseStop;};
// No generic success event, menu reopen, or unconditional speed/stance reset: the shared pose stop owns all of it.
if (_success && {local _medic} && {alive _medic}
    && {(_record select 7) == (_medic getVariable ["ACME_providerLocalityEpoch", 0])}
    && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {(_record select 4) >= 0} && {CBA_missionTime - (_record select 4) >= 1.5}) then {
    (_record select 1) call ACME_fnc_feelSkin;
};
