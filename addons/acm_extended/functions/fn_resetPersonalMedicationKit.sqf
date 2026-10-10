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

[_unit, []] call ACME_fnc_narcStoreCommit;
[_unit, createHashMap] call ACME_fnc_openVialStoreCommit;
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
