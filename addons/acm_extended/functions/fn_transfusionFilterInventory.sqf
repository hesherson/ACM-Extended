/* B275: rebuild only when the Y-set saline picker enters or leaves its step.
 * Native inventory rows and the cooler/used overlays share this mode; no
 * prepared custody or active patient bag state is hidden or changed here. */
private _display = findDisplay 86000;
if (isNull _display) exitWith {false};
private _selectingSaline = !(uiNamespace getVariable ["ACME_preparedListMode", false])
    && {(missionNamespace getVariable ["ACME_yPending", ""]) != ""}
    && {(missionNamespace getVariable ["ACME_yPendingSaline", ""]) == ""};
private _pending = missionNamespace getVariable ["ACME_piggybackPending",[]];
private _current = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]];
if (_pending isNotEqualTo [] && {count _pending < 6 || {!((_pending select [0,4]) isEqualTo _current)}
    || {(_pending select 5) != ([_pending select 0] call ACME_fnc_clinicalEpoch)}
    || {!(_current call ACME_fnc_piggybackEligible)}}) then {
    ["cancel"] call ACME_fnc_piggybackWorkflow;
    _pending = [];
};
private _pickerSignature = str [_selectingSaline,_pending];
if ((_display getVariable ["ACME_txPickerSignature", ""]) != _pickerSignature) then {
    _display setVariable ["ACME_txPickerSignature",_pickerSignature];
    _display setVariable ["ACME_txSalinePicker", _selectingSaline];
    if (!isNil "ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory") then {
        [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
    };
    uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
    uiNamespace setVariable ["ACME_usedRowSig", "__force__"];
};
_selectingSaline
