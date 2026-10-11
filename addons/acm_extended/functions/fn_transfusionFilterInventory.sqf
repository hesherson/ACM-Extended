/* B274: rebuild only when the Y-set saline picker enters or leaves its step.
 * Native inventory rows and the cooler/used overlays share this mode; no
 * prepared custody or active patient bag state is hidden or changed here. */
private _display = findDisplay 86000;
if (isNull _display) exitWith {false};
private _selectingSaline = !(uiNamespace getVariable ["ACME_preparedListMode", false])
    && {(missionNamespace getVariable ["ACME_yPending", ""]) != ""}
    && {(missionNamespace getVariable ["ACME_yPendingSaline", ""]) == ""};
if ((_display getVariable ["ACME_txSalinePicker", false]) isNotEqualTo _selectingSaline) then {
    _display setVariable ["ACME_txSalinePicker", _selectingSaline];
    if (!isNil "ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory") then {
        [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
    };
    uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
    uiNamespace setVariable ["ACME_usedRowSig", "__force__"];
};
_selectingSaline
