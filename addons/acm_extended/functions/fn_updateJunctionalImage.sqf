// the junctional wound and wrap body-image overlays.
// it is the same proven pattern as the NRB-mask overlay: we do not config-merge into ACM's
// ace_medical_gui_BodyImage, because that drops the inherited silhouette and blanks the whole image.
// instead we listen on ACM's own draw event, "ace_medical_gui_updateBodyImage", and create the overlay controls at
// runtime, parented to the live control group, cloning the position of torso_io, idc 70113. every ACM body icon
// clones that full-image rect, and each per-limb texture paints its mark at the correct spot, so the position is
// automatic.
// on layering: runtime-created controls render on top of ACM's config icons. arma has no runtime z-reorder and a
// config-merge blanks the image, so the wraps cannot be forced beneath ACM's icons. on a wrapped limb the wrap
// will sit over any iv, io or tourniquet icon there. see the readme note.
// the state per limb is _target getvariable ["ACME_Junc_<part>", ""], which is "", "open", "packed", "xstat" or "wrapped".
// open shows the open-wound icon. packed shows the dedicated packed-gauze icon supplied for that limb.
// wrapped shows the pressure-wrap icon, meaning healed and secured, and hides the wound/packed icon.

params ["_ctrlGroup", "_target"];
if (isNull _ctrlGroup) exitWith {};

private _ref = _ctrlGroup controlsGroupCtrl 70113;  // idc_body_torso_io, the full-image rect all the icons clone.

// Each junction now uses three independent layers:
//   base wound (always visible for open/packed/xstat),
//   treatment overlay (combat gauze or XStat, visible on top of the base wound),
//   pressure wrap (wrapped state only).
// Packing therefore never replaces or hides the underlying wound art.
// 7290020/21 belong to the EJ icons and their access-site hit targets.
// Packing needs its own control IDs so handler order cannot replace device artwork.
private _limbs = [
    ["leftarm",  7290000, 7290004, 7290040, "junctionalwrap_leftarm_ca.paa",  "junctionalwound_leftarm_ca.paa",  "junctionalwound_packed_leftarm_ca.paa",  "junctionalwound_xstat_leftarm_ca.paa"],
    ["rightarm", 7290001, 7290005, 7290041, "junctionalwrap_rightarm_ca.paa", "junctionalwound_rightarm_ca.paa", "junctionalwound_packed_rightarm_ca.paa", "junctionalwound_xstat_rightarm_ca.paa"],
    ["leftleg",  7290002, 7290006, 7290042, "junctionalwrap_leftleg_ca.paa",  "junctionalwound_leftleg_ca.paa",  "junctionalwound_packed_leftleg_ca.paa",  "junctionalwound_xstat_leftleg_ca.paa"],
    ["rightleg", 7290003, 7290007, 7290043, "junctionalwrap_rightleg_ca.paa", "junctionalwound_rightleg_ca.paa", "junctionalwound_packed_rightleg_ca.paa", "junctionalwound_xstat_rightleg_ca.paa"]
];

// israeli pressure bandage olive green. the wrap depicts a physical bandage rather than a status, so it no longer
// borrows the shared warning yellow, which stays untouched for the systems that use it semantically.
private _wrapColor = missionNamespace getVariable ["ACME_junctionalWrapColor", [0.38, 0.42, 0.28, 1]];

{
    _x params ["_part", "_wrapIdc", "_woundIdc", "_packedIdc", "_wrapTex", "_openTex", "_packedTex", "_xstatTex"];

    private _state = if (isNull _target) then {""} else {
        toLowerANSI (_target getVariable [format ["ACME_Junc_%1", _part], ""])
    };

    // Base wound first. This is the permanent underlying tissue injury for every non-wrapped active junction.
    private _woundC = _ctrlGroup controlsGroupCtrl _woundIdc;
    if (isNull _woundC) then {
        _woundC = (ctrlParent _ctrlGroup) ctrlCreate ["RscPicture", _woundIdc, _ctrlGroup];
    };

    // Treatment overlay second, so gauze/XStat is composited over the unchanged wound texture.
    private _packedC = _ctrlGroup controlsGroupCtrl _packedIdc;
    if (isNull _packedC) then {
        _packedC = (ctrlParent _ctrlGroup) ctrlCreate ["RscPicture", _packedIdc, _ctrlGroup];
    };

    // Pressure wrap is a separate terminal presentation and hides the open wound/treatment layers.
    private _wrapC = _ctrlGroup controlsGroupCtrl _wrapIdc;
    if (isNull _wrapC) then {
        _wrapC = (ctrlParent _ctrlGroup) ctrlCreate ["RscPicture", _wrapIdc, _ctrlGroup];
    };

    if (!isNull _ref) then {
        private _rect = ctrlPosition _ref;
        _woundC ctrlSetPosition _rect;
        _packedC ctrlSetPosition _rect;
        _wrapC ctrlSetPosition _rect;
    };

    // XStat stays on the original proven body-map control; combat gauze alone uses the added overlay layer.
    _woundC ctrlSetText ("\acm_extended\ui\items\" + (if (_state == "xstat") then {_xstatTex} else {_openTex}));
    _packedC ctrlSetText ("\acm_extended\ui\items\" + _packedTex);
    _wrapC ctrlSetText ("\acm_extended\ui\items\" + _wrapTex);
    _wrapC ctrlSetTextColor _wrapColor;

    // Junctional evidence is clinical state, not a UI transition. Never fade these controls in: the wound and
    // newly packed device appear on the exact GUI refresh where the authoritative state changes.
    {
        _x ctrlSetFade 0;
        _x ctrlCommit 0;
    } forEach [_woundC, _packedC, _wrapC];

    _woundC ctrlShow (_state in ["open", "packed", "xstat"]);
    _packedC ctrlShow (_state == "packed");
    _wrapC ctrlShow (_state == "wrapped");
} forEach _limbs;

// Standard tourniquet controls are config-created before these runtime junctional wraps, so the wrap would
// otherwise render on top of a tourniquet. Mirror the four native tourniquet pictures into a dedicated top layer.
// The source control remains untouched for ACE/ACM state logic; this copy is presentation-only.
private _tqTop = [
    [6035, 7290014],
    [6040, 7290015],
    [6045, 7290016],
    [6050, 7290017]
];
{
    _x params ["_sourceIdc", "_topIdc"];
    private _source = _ctrlGroup controlsGroupCtrl _sourceIdc;
    private _top = _ctrlGroup controlsGroupCtrl _topIdc;
    if (isNull _top) then {
        _top = (ctrlParent _ctrlGroup) ctrlCreate ["RscPicture", _topIdc, _ctrlGroup];
    };
    if (isNull _source) then {
        _top ctrlShow false;
    } else {
        _top ctrlSetPosition (ctrlPosition _source);
        _top ctrlSetText (ctrlText _source);
        // Match ACE's native body-map tourniquet tint exactly. B111's top-layer copy used white, which made
        // the overlay stack correct but visually regressed the tourniquets.
        _top ctrlSetTextColor [0, 0, 0.8, 1];
        _top ctrlCommit 0;
        _top ctrlShow (ctrlShown _source);
    };
} forEach _tqTop;

// the NAR AAJT-s overlays.
// they are created after the wound and wrap controls, and being runtime controls they sit above all of ACM's config
// icons, the iv, io and tourniquet and the AED pads, so the device always sits on top, as required. the inguinal
// one sits over the groin and the axilla icons sit over each armpit. they are shown from the per-placement flags
// set by fn_aajtapply.
private _aajt = [
    [7290010, "aajt-s_inguinal_ca.paa",      (!isNull _target && {_target getVariable ["ACME_AAJT_inguinal",   false]})],
    [7290011, "aajt-s_axilla_left_ca.paa",   (!isNull _target && {_target getVariable ["ACME_AAJT_axillaleft",  false]})],
    [7290012, "aajt-s_axilla_right_ca.paa",  (!isNull _target && {_target getVariable ["ACME_AAJT_axillaright", false]})],
    [7290013, "aajt-s_zone3_reboa_ca.paa",   (!isNull _target && {_target getVariable ["ACME_AAJT_zone3",       false]})]
];
{
    _x params ["_idc", "_tex", "_on"];
    private _c = _ctrlGroup controlsGroupCtrl _idc;
    if (isNull _c) then {
        _c = (ctrlParent _ctrlGroup) ctrlCreate ["RscPicture", _idc, _ctrlGroup];
        if (!isNull _ref) then { _c ctrlSetPosition (ctrlPosition _ref); };
        _c ctrlSetText ("\acm_extended\ui\items\" + _tex);
        _c ctrlCommit 0;
    };
    _c ctrlShow _on;
} forEach _aajt;
