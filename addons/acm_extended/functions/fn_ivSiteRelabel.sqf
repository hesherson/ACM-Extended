// hardcore IV and IO site descriptors, as a pure text transform.
// call it as [_text, _selectionN, _isButton, _actionClass] call ACME_fnc_ivSiteRelabel, which returns the rewritten text.
// _selectionN is the ACE body part index: 0 head, 1 body, 2 leftarm, 3 rightarm, 4 leftleg, 5 rightleg.
// _isButton is true for a medical-menu action button and false for an injury-list row. buttons additionally
// lose the leading verb and take the position descriptors, and rows do not.
//
// this used to be a per-frame PFH that repainted ACE's buttons and listbox after ACE had already drawn them.
// two things were wrong with that. the PFH only started if hardcore was already on when the menu opened, so
// toggling the setting with the menu up did nothing until it was reopened. and it had no idea which limb a
// row belonged to, so it guessed from the row text with (_lowT find "arm" >= 0). ACM builds those rows as
// "16g IV (Middle)" with no limb word in them, so that test was false on every single row and every arm IV
// in the injury list was being labelled with the LEG vein name.
// both callers now hand in the real selection index, and both call sites are places we already own:
// overrides/fn_updateActions.sqf for the buttons and the ace_medical_gui_updateInjuryListPart event for the
// rows.
//
// the names come from ACME_fnc_skSiteName, which reads ACME_fnc_ivVeinCatalog. one source of truth, so the
// body map, the buttons, the injury list and the difficulty model cannot drift apart again.
params [["_text", ""], ["_selectionN", -1], ["_isButton", false], ["_actionClass", ""]];
if (_text isEqualTo "") exitWith { _text };
if (_isButton && {toLowerANSI _actionClass == "insertio_ez"}) exitWith {
    if (_selectionN in [2,3]) then {"Insert EZ-IO (Humeral Head)"} else {"Insert EZ-IO (Tibial Tuberosity)"}
};
// Resolve posture by stable action class before the clinical gate or generic
// "Place " trimming. Indented children retain their indentation in both modes.
private _positionKey = "";
private _leading = 0;
if (_isButton) then {
    private _chars = toArray _text;
    while {_leading < count _chars && {(_chars select _leading) in [9,32]}} do {
        _leading = _leading + 1;
    };
    switch (toLower _actionClass) do {
        case "acme_elevatehead": {_positionKey = "elevate30";};
        case "acme_lowerhead": {_positionKey = "lower0";};
    };
    // Compatibility for direct callers that do not supply collected class metadata.
    if (_positionKey == "" && {_actionClass == ""}) then {
        private _label = toLower (_text select [_leading]);
        if ((_label find "elevate head to 30") == 0 || {_label == "place in semi-fowler's position"}) then {_positionKey = "elevate30";};
        if (_label == "lower head to flat" || {_label == "place in supine position"}) then {_positionKey = "lower0";};
    };
};
if (_positionKey != "") exitWith {
    (_text select [0,_leading]) + (["position", _positionKey] call ACME_fnc_medDescriptor)
};
if (!(((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true))) exitWith { _text };

private _bp = ["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"] param [_selectionN, ""];
private _new = _text;

// the tokens to look for.
// this used to be the three English literals "(Upper)", "(Middle)" and "(Lower)". that is wrong on any
// localized game: ACM builds its rows from STR_ACM_Circulation_IV_Upper and friends, so on a German or French
// client the row says something else, the literal never matches, and the ENTIRE site relabel silently does
// nothing. fn_ivLogRelabel already resolved this correctly with localize and this did not, which is the kind
// of inconsistency that only surfaces as a bug report from somebody else's server.
// both forms are matched. the localized one covers ACM's rows and ACM's own action displayNames, and the
// English one covers our own 18g actions in config.cpp, whose displayNames are English literals we wrote.
private _tokens = [];
{
    _x params ["_key", "_idx"];
    private _loc = format ["(%1)", localize _key];
    _tokens pushBack [_loc, _idx];
    private _eng = format ["(%1)", ["Upper", "Middle", "Lower"] select _idx];
    if (_eng isNotEqualTo _loc) then { _tokens pushBack [_eng, _idx]; };
} forEach [
    ["STR_ACM_Circulation_IV_Upper", 0],
    ["STR_ACM_Circulation_IV_Middle", 1],
    ["STR_ACM_Circulation_IV_Lower", 2]
];

// IV sites only exist on the limbs. the head carries the EJ, which fn_postInit relabels on its own because
// ACM gives it no upper, middle or lower token to swap.
if (_bp in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
    // THE LABEL DIAGNOSTIC IS REMOVED.
    // it wrote four RPT lines on EVERY render of the medical menu, and it defaulted to on. one log reached
    // 868,225 lines and 61 MB. a menu render is the hottest text path in the addon and it must write nothing.
    // ACME_iv_siteDebug is no longer read by anything.
    {
        _x params ["_token", "_site"];
        if (_new find _token > -1) then {
            private _name = [_bp, _site, false] call ACME_fnc_skSiteName;
            if (_name isNotEqualTo "") then {
                _new = [_new, _token, format ["(%1)", _name]] call CBA_fnc_replace;
            };
        };
    } forEach _tokens;

    // IO lines carry no site token from ACM, so the anatomical IO site is appended instead of swapped.
    // the injury list gets this too. it used to be button-only, which left a row reading "EZ-IO" sitting
    // directly under a button reading "EZ-IO (Humeral Head)".
    if ((_new find "EZ-IO" > -1) || {_new find "FAST1" > -1}) then {
        if (_new find "(" < 0) then {
            _new = _new + format [" (%1)", [_bp, 0, true] call ACME_fnc_skSiteName];
        };
    };
};

if (!_isButton) exitWith { _new };

// button-only from here down.
// "14g IV (Median Cubital)". the IV stays, because it is the route, and the route plus the bore plus the vein
// is how a line gets described out loud and written on a card. only the verb goes, because the position of the
// button already says it is a placement.
if (_new find "Place " == 0) then { _new = _new select [6]; };

// Position actions were resolved above, before clinical gating and verb trimming.

_new
