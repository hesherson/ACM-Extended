/* B294: replace the existing fluid-card surface inside the existing transfusion display. */
params ["_display"];
if (isNull _display || {!(_display isEqualTo findDisplay 86000)}) exitWith {false};
if (!(missionNamespace getVariable ["ACME_reactTransfusion",false])
    || {_display getVariable ["ACME_reactFailed",false]}) exitWith {
    if (_display getVariable ["ACME_reactActive",false]) then {[_display] call ACME_fnc_reactMedicalFallback;};
    false
};
private _layout = (_display getVariable ["ACME_txCardLayout",createHashMap]) getOrDefault [86004,[]];
if (count _layout != 5) exitWith {false};
private _browser = _display displayCtrl 89301;
if (isNull _browser) then {
    private _medic = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Medic",objNull];
    private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
    if (isNull _medic || {isNull _patient}) exitWith {};
    private _context = [_medic,_patient,"",[],[_patient] call ACME_fnc_clinicalEpoch,
        _patient getVariable ["ACME_equipmentKitEpoch",0],_medic getVariable ["ACME_equipmentKitEpoch",0],
        _medic getVariable ["ACME_providerLocalityEpoch",0],owner _patient];
    if !([_context] call ACME_fnc_reactMedicalValid) exitWith {};
    _display setVariable ["ACME_reactContext",_context];
    _display setVariable ["ACME_reactDeadline",diag_tickTime + 6];
    _display setVariable ["ACME_reactFailed",false];
    _browser = _display ctrlCreate ["ACME_ReactTransfusionCards",89301];
    if (isNull _browser) exitWith {_display setVariable ["ACME_reactFailed",true];};
    _browser ctrlShow false;
    [_browser,"position",_layout select 0] call ACME_fnc_transfusionUiSet;
    _browser setVariable ["ACME_txListIDC",86004];
    _browser setVariable ["ACME_txCapacity",2];
    _display displayAddEventHandler ["Unload",{_this call ACME_fnc_reactMedicalClose;}];
    _browser ctrlWebBrowserAction ["LoadFile","acm_extended\ui\react\index.html"];
};
if (isNull _browser) exitWith {false};
[_display] call ACME_fnc_reactMedicalTick;
_display getVariable ["ACME_reactActive",false]
