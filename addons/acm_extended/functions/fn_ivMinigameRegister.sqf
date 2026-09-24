// register the completed iv placement in ACM, so the patient gets the real iv, and ACM's native body-image icon at
// the correct site. the mini-game has already determined success, so we drive ACM's local setter directly,
// bypassing its own systolic success roll. it maps the mini-game site and gauge to ACM's parameters.
// the ACM setivlocal args are [_medic, _patient, _bodyPart, _state, which is the type, _iv as true, _accessSite].
// the accesssite is 0 for upper, 1 for middle and 2 for lower.
// the type and state is acm_iv_16g_m and the like, and we map the gauge to the ACM gauge constant.
private _medic    = uiNamespace getVariable ["ACME_IV_Medic", objNull];
if !([] call ACME_fnc_ivUiValid) exitWith {};
private _patient  = uiNamespace getVariable ["ACME_IV_Patient", objNull];
private _bodyPart = toLower (uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"]);
private _gauge    = uiNamespace getVariable ["ACME_IV_InsGauge", 16];
// The caller must know if this function placed an IV. The caller then decides to draw a hub.
// CAUTION: A hub with no IV is a catheter that the medic can pull. ACM does not know that catheter.
uiNamespace setVariable ["ACME_IV_RegOK", false];
if (isNull _patient) exitWith {};

// THE SITE COMES FROM THE PUNCTURE.
// This function read ACME_IV_Site before. That value is the band site.
// Any code can change that value while the dialog is open.
// Each reader in the chain used a different default value for an unset site.
// Three of those defaults gave "lower". An antecubital stick then recorded a lower cephalic IV.
// The RPT could not show the fault. The correct value and the three failures all read as "lower".
// fn_ivMinigameInsertStart writes ACME_IV_InsSite once, from the coordinates of the puncture.
// No other code changes that value.
// CAUTION: There is no default value. An unknown site places no IV.
private _site = "";
if (_bodyPart == "ej") then {
    // The EJ uses a different path. The side is the anatomical side of the patient.
    // fn_ivMinigameStickSuccess locks that side.
    // The EJ art uses the opposite names. Therefore the puncture point cannot give the side.
    _site = toLower (uiNamespace getVariable ["ACME_IV_Site", ""]);
    if !(_site in ["left", "right"]) then { _site = ""; };
} else {
    _site = toLower (uiNamespace getVariable ["ACME_IV_InsSite", ""]);
    if !(_site in ["upper", "middle", "lower"]) then { _site = ""; };
};
if (_site isEqualTo "") exitWith {
    // This block is a guard. Normal use does not reach it.
    // fn_ivMinigameClick refuses a stick with an unknown site.
    // The code reaches this block only if the insertion state is lost after the puncture.

};

private _accessSite = [_site] call ACME_fnc_ivSiteIndex;

// THE ACTIVITY LOG LINE.
// ACM writes its own log inside ACM_circulation_fnc_setIV, above the setIVLocal event, at
// circulation/functions/fnc_setIV.sqf:179. This function drives setIVLocal directly, to skip ACM's systolic
// success roll, so that log line never runs and an IV placed through the mini-game left no record. The line is
// written here instead.
// The side letter and the vein shorthand are resolved NOW, because the ej remap below replaces the body part
// with "head" and the shorthand would then read as a head site.
// ACME_fnc_ivLogSite owns the wording. fn_ivMinigamePullStop writes the removal line and reads the same
// function, so a placement and its removal always name the same site.
private _siteText = [_bodyPart, _site] call ACME_fnc_ivLogSite;

// the ej has no dedicated ACM body part. it is modeled on the head, which is a valid ACM and ACE part, with left
// and right on access sites 0 and 1, so both jugulars can co-exist. ACM then treats it as a normal iv on the
// head, so fluids flow and the native body-image icon and the removal all work. if a head iv ever misbehaves in
// ACM, remap _bodyPart here to "body".
if (_bodyPart == "ej") then { _bodyPart = "head"; };

// the ACM gauge type values are compile-time macros: acm_iv_16g_m is 1 and acm_iv_14g_m is 2. ACME adds a distinct
// 18g, type 5, so the smaller bore flows slower through the getIVFlowRate override, using ACME_iv18gFlowFactor,
// matching a real 18g at about half a 16g. the 16g stays the default marker, the 14g is faster and the 18g is
// slower.
// setivlocal stores the type directly and does not schedule ACM's 16g and 14g specific complications, because those
// key on type 1 or 2, so an 18g simply does not fire them. that is fine, because the mod's own distal-drip
// hazard, which is site-based, still applies.
private _type = 1;  // 16g, the base flow.
if (_gauge == 14) then { _type = 2; };  // 14g, a faster flow.
if (_gauge == 18) then { _type = 5; };  // 18g, a slower, smaller-bore flow.
if (_gauge == 20) then { _type = 6; };  // 20g, the smallest bore and the slowest flow.

// consume one catheter from the inventory of the medic, which is the item of the iv action.
if (!isNull _medic) then {
    private _cl = format ["ACM_IV_%1g", _gauge];  // the 14g, 16g and 18g each consume their own catheter.
    if (([_medic, _cl] call ACME_fnc_itemCount) > 0) then { [_medic, _cl] call ACME_fnc_itemTake; };
};

// Owner/episode-checked single-site commit. No delayed whole-row repair.
[_patient, "ivSite", [_medic, _patient, _bodyPart, _type, _accessSite,
    [_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;

// The log uses anatomical shorthand only with Clinical Descriptors enabled. Otherwise it names the limb and site.
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _who = "";
    if (!isNull _medic) then { _who = [_medic, false, true] call ace_common_fnc_getName; };
    if (_who isEqualTo "") then {
        // No medic object. The sentence drops the name rather than inventing one.
        if (_siteText isEqualTo "") then {
            [_patient, "activity", "Established IV", []] call ace_medical_treatment_fnc_addToLog;
        } else {
            [_patient, "activity", "Established IV, %1", [_siteText]] call ace_medical_treatment_fnc_addToLog;
        };
    } else {
        if (_siteText isEqualTo "") then {
            [_patient, "activity", "%1 established IV", [_who]] call ace_medical_treatment_fnc_addToLog;
        } else {
            [_patient, "activity", "%1 established IV, %2", [_who, _siteText]] call ace_medical_treatment_fnc_addToLog;
        };
    };
};

uiNamespace setVariable ["ACME_IV_RegOK", true];

// the extravasation site check. if this iv was placed distal to, meaning below, a compromised site on the same
// limb, which is a previous miss or the venotomy of a removed iv, it will leak: a drug pushed through it flows
// proximally and escapes the hole.
// flag it, so the vesicant eh forces extravasation for any drug delivered here, whatever the threshold of the drug
// itself. the medic should have placed the iv above every hole. it is keyed by the ACM body part and access site,
// so the flag is per-iv and clears when the iv is removed.
private _stickV = uiNamespace getVariable ["ACME_IV_StickV", 0.5];
private _willLeak = [_patient, _site, _stickV] call ACME_fnc_ivExtravasationCheck;
private _flagKey = format ["ACME_ivCompromised_%1_%2", _bodyPart, _accessSite];
[_patient, "ivCompromised", [_bodyPart, _accessSite, ["clear", "set"] select _willLeak]] call ACME_fnc_ownerDispatch;
// Compromise remains physiological state; placement does not disclose the hidden risk.
