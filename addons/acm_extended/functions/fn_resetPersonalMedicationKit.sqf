/* Reset hidden medication-container state when a player receives a fresh kit.
 *
 * Prepared syringes and opened-vial remainder are virtual state layered on top of physical inventory.
 * A wholesale kit reload can restore the consumed vial/syringe items without replacing the player object,
 * so these ledgers must be reset explicitly or the old virtual contents duplicate into the fresh loadout.
 */
params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith {false};

// Invalidate this kit's active controller before replacing its rows. Otherwise the next queued tick sees a
// missing syringe, cannot restore its unsent tail, and re-creates a retired blocker after the fresh-kit reset.
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if (_job isEqualType createHashMap && {count _job > 0}
    && {(_job getOrDefault ["medic",objNull]) isEqualTo _unit}) then {
    private _session = _job getOrDefault ["session",""];
    private _pfh = missionNamespace getVariable ["ACME_HCMedPushPFH",-1];
    if ([_session,_pfh,"kit-reset"] call ACME_fnc_hardcorePushRetire) then {
        // A full retirement archive keeps the active record in place. This explicit kit replacement also
        // invalidates that inventory, but must never clear a newer/different controller.
        private _current = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
        if (_current isEqualType createHashMap && {(_current getOrDefault ["session",""]) == _session}
            && {(_current getOrDefault ["medic",objNull]) isEqualTo _unit}) then {
            missionNamespace setVariable ["ACME_HCMedPushJob",createHashMap];
        };
    };
};

// A deliberately replaced kit discards its old plunger accounting, while an
// already-dispatched patient request must still receive its immutable terminal
// decision. Copy settlement metadata only: field 1 remains the original wire
// arguments, including their hcPush metadata, for safe patient retries.
private _escrow = _unit getVariable ["ACME_medicationEscrow",createHashMap];
private _marked = false;
{
    private _row = _escrow get _x;
    private _meta = _row param [5,[]];
    if (_meta isEqualType [] && {(_meta param [0,""]) == "hcPush"}) then {
        private _copy = +_row;
        private _retiredMeta = +_meta; _retiredMeta set [0,"hcPushKitReset"];
        _copy set [5,_retiredMeta]; _escrow set [_x,_copy];
        _marked = true;
    };
} forEach (keys _escrow);
if (_marked) then {[_unit,_escrow] call ACME_fnc_medicationEscrowCommit;};

[_unit, []] call ACME_fnc_narcStoreCommit;
[_unit, createHashMap] call ACME_fnc_openVialStoreCommit;
// Old journals keep immutable patient decisions, but cannot fund this replacement kit.
if (!isNil "ACME_fnc_syringeDeliveryRecover") then {[_unit,true] call ACME_fnc_syringeDeliveryRecover;};
_unit setVariable ["ACME_narcStoreSerial", 0, false];
// A deliberate fresh-kit replacement invalidates retired syringe inventory from that provider's previous kit.
private _retired = missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",_retired select {!((_x select 0) isEqualTo _unit)}];

if (hasInterface && {_unit isEqualTo ACE_player}) then {
    [_unit] call ACME_fnc_vialLeaseRelease;

    uiNamespace setVariable ["ACME_SK_SelectedSyringeId", ""];
    uiNamespace setVariable ["ACME_SK_CarouselIdx", -1];
    uiNamespace setVariable ["ACME_SK_SelDrawn", -1];
    uiNamespace setVariable ["ACME_SK_SiteIdx", -1];
    uiNamespace setVariable ["ACME_SK_OpenCarouselId", ""];
    uiNamespace setVariable ["ACME_SK_PendingInjection", []];
    uiNamespace setVariable ["ACME_SK_VialHolder", objNull];
    uiNamespace setVariable ["ACME_SK_CompoundComponents", []];
    uiNamespace setVariable ["ACME_SK_CompoundVials", []];
    uiNamespace setVariable ["ACME_SK_WasteStage", ""];
    uiNamespace setVariable ["ACME_SK_DiscardArmedId", ""];
};

true
