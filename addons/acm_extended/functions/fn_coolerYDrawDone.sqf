/* Complete only the exact owned Y draw. Its delivered bag remains physical
 * when UI intent is canceled; this callback never refunds or mints a product. */
params ["_ok","_args"];
_args params ["_serial","_context"];
private _request = [_serial,_context];
if ((missionNamespace getVariable ["ACME_yCoolerDrawPending",[]]) isNotEqualTo _request) exitWith {};
private _owner = _context select 0;
private _dialog = findDisplay 86000;
private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _valid = _ok && {!isNull _dialog} && {!isNull _owner} && {_owner isEqualTo ACE_player}
    && {local _owner} && {alive _owner} && {!(_owner getVariable ["ACE_isUnconscious",false])}
    && {_owner isEqualTo (call ACME_fnc_controlledProvider)}
    && {!(_owner getVariable ["ACME_persistenceFrozen",false])}
    && {isNull _target || {!(_target getVariable ["ACME_persistenceFrozen",false])}}
    && {!(uiNamespace getVariable ["ACME_preparedListMode",false])}
    && {(missionNamespace getVariable ["ACME_piggybackPending",[]]) isEqualTo []}
    && {(missionNamespace getVariable ["ACME_yBuildPending",[]]) isEqualTo []};
if (_valid) then {
    private _current = [_owner,_target,
        missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
        missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
        missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],
        missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0],
        _owner getVariable ["ACME_equipmentKitEpoch",0],
        _owner getVariable ["ACME_providerLocalityEpoch",0],
        missionNamespace getVariable ["ACME_yPending",""],missionNamespace getVariable ["ACME_yPendingSaline",""],
        missionNamespace getVariable ["ACME_yPendingData",""],missionNamespace getVariable ["ACME_yPendingSalineData",""],
        missionNamespace getVariable ["ACME_yPendingBloodUsedId",""],missionNamespace getVariable ["ACME_yPendingSalineUsedId",""],
        if (isNull _target) then {-1} else {[_target] call ACME_fnc_clinicalEpoch}];
    _valid = _current isEqualTo _context;
};
// Retire only this still-owned request. A newer build owns its own recipe.
if ((missionNamespace getVariable ["ACME_yCoolerDrawPending",[]]) isNotEqualTo _request) exitWith {};
if (!_valid && {(missionNamespace getVariable ["ACME_yBuildPending",[]]) isEqualTo []}) then {
    missionNamespace setVariable ["ACME_yPending", ""];
    missionNamespace setVariable ["ACME_yPendingData", ""];
    missionNamespace setVariable ["ACME_yPendingSaline", ""];
    missionNamespace setVariable ["ACME_yPendingSalineData", ""];
    missionNamespace setVariable ["ACME_yPendingBloodVol", 0];
    missionNamespace setVariable ["ACME_yPendingSalineVol", 0];
    missionNamespace setVariable ["ACME_yPendingBloodUsedId", ""];
    missionNamespace setVariable ["ACME_yPendingSalineUsedId", ""];
    missionNamespace setVariable ["ACME_yPendingBloodUsedRow", []];
    missionNamespace setVariable ["ACME_yPendingSalineUsedRow", []];
    missionNamespace setVariable ["ACME_yPendingPatient", objNull];
    missionNamespace setVariable ["ACME_ySelExactVol", 0];
    missionNamespace setVariable ["ACME_ySelUsedId", ""];
    missionNamespace setVariable ["ACME_ySelUsedRow", []];
};
missionNamespace setVariable ["ACME_yCoolerDrawPending",[]];
if (_valid) exitWith {[_context] call ACME_fnc_transfusionYTubing;};
// Raw ownership cleanup is complete before any refresh that can fail/re-enter.
if (!isNull _dialog && {_owner isEqualTo ACE_player}) then {
    call ACME_fnc_transfusionFilterInventory;
    call ACME_fnc_updateTransfusionControls;
};
