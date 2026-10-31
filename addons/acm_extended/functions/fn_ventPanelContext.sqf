/* A panel controls the exact device/clinical episode captured by its onLoad.
 * Recheck before input as well as in the PFH: an old callback can arrive before
 * the next frame notices a recovery, kit replacement or provider switch.
 * Closing an unreachable panel never stops the patient-mounted ventilator.
 */
disableSerialization;
private _panel = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _panel) exitWith {false};
private _context = _panel getVariable ["ACME_vent_context", []];
if (!(_context isEqualType []) || {count _context != 5}) exitWith {false};
_context params ["_provider", "_target", "_epoch", "_custody", "_kitEpoch"];
if (isNull _provider || {isNull _target} || {!local _provider} || {!alive _provider}
    || {_provider getVariable ["ACE_isUnconscious", false]}
    || {_provider getVariable ["ACME_persistenceFrozen", false]}
    || {_target getVariable ["ACME_persistenceFrozen", false]}
    || {_provider isNotEqualTo (call ACME_fnc_controlledProvider)}
    || {(_panel getVariable ["ACME_vent_viewer", objNull]) isNotEqualTo _provider}
    || {(uiNamespace getVariable ["ACME_vent_target", objNull]) isNotEqualTo _target}
    || {([_target] call ACME_fnc_clinicalEpoch) != _epoch}
    || {(_target getVariable ["ACME_vent_custodyId", ""]) != _custody}
    || {!([_provider, "ventilator", true] call ACME_fnc_procedureAllowed)}) exitWith {false};
if (_provider isEqualTo _target) exitWith {
    (_provider getVariable ["ACME_equipmentKitEpoch", 0]) == _kitEpoch
        && {([_provider, "ACME_Ventilator"] call ace_common_fnc_getCountOfItem) > 0}
};
(_target getVariable ["ACME_vent_onPatient", false])
    && {!(_target getVariable ["ACME_vent_recovering", false])}
    && {[_provider, _target] call ACME_fnc_ventRecoveryNear}
