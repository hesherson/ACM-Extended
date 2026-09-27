// the shared y-line attach and saline-clamp sequence. it hangs a blood unit and its paired saline on one y line,
// then clamps the saline limb so it holds as the priming and flush reserve instead of transfusing.
// it is extracted verbatim from the original two-press "Spike Y tubing" tail, so both the former direct-hang path
// and the new hang-set-from-a-prepared-set path use the exact same proven retag logic. this is the code that
// fixes the recurring y saline still transfuses drain.
// callers are responsible for consuming the physical items and, for a cold unit, for banking ACME_ySetsCooled
// before calling, so the unit still hangs [cooled].
// the params are [_target, _bodyPart, _iv, _site, _lineKey, _blood, _bloodAction, _saline, _salineAction].
params ["_target", "_bodyPart", "_iv", "_site", "_lineKey", "_blood", "_bloodAction", "_saline", "_salineAction"];
if (isNull _target) exitWith {};
if !([_target,_bodyPart,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {
    ["An established IV/IO is required before hanging a Y-line.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;
};

// hang both limbs on the line in one shot through the ivbag attach of ACE and ACM, with no 5 s addbag and no
// double menu trip. the blood goes on first so it sits above the saline in the list. the blood flows normally
// and the saline is held clamped, because the blood-volume override skips draining a saline bag on a y'd line,
// so it sits as the priming and flush reserve.
[ACE_player, _target, _bodyPart, _bloodAction,   objNull, _blood,  _iv, _site] call ace_medical_treatment_fnc_ivBag;
[ACE_player, _target, _bodyPart, _salineAction,  objNull, _saline, _iv, _site] call ace_medical_treatment_fnc_ivBag;

// a synchronous same-frame retag. ivbag fires ivbaglocal through CBA_fnc_targetEvent, which for a local patient
// runs immediately, so the saline entry is already in IV_Bags, as type "Saline", right now. retag it to the clamp
// sentinel ACME_SalineY this frame, before any medical tick can drain it.
// this is the authoritative fix for the y saline still transfusing: it no longer depends on ACME_YLines prefix
// matching, the delayed owner-side targetevent, or the self-heal of the override. the type is the clamp the
// moment the bag is hung. the owner-side setup and self-heal below remain as backstops for the non-local and
// late-sync cases.
if (local _target) then {
    private _bags = _target getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _arr = _bags getOrDefault [_bodyPart, []];
    // retag the most recently hung matching saline, so the last index wins, because the blood went on first and the
    // saline second.
    private _sIdx = -1;
    {
        if (((_x param [0, ""]) == "Saline") && {(_x param [4, true]) isEqualTo _iv} && {(_x param [3, -1]) isEqualTo _site}) then { _sIdx = _forEachIndex; };
    } forEach _arr;
    if (_sIdx >= 0) then {
        private _e = +(_arr select _sIdx);
        _e set [0, "ACME_SalineY"];
        _arr set [_sIdx, _e];
        _bags set [_bodyPart, _arr];
        [_target, _bags] call ACME_fnc_ivBagsCommit;
    };
};

// the authoritative retag on the owning machine of the casualty, where the bag drainer runs and IV_Bags is owned.
// this is the real fix for the recurring drain: the medic-side retag below can be clobbered by the per-tick write
// of the owner before its own override sees ACME_SalineY. fn_ysalinesetup runs after the ivbaglocal events, and
// retries, so it re-types the saline locally on the owner and the type clamp holds. it is a harmless no-op when
// the medic is the owner.
["ACME_ySalineSetup", [_target, _lineKey, _iv], _target] call CBA_fnc_targetEvent;

// record the completed intervention in the activity log of the patient.
[_target, "activity", "%1 hung blood on a Y-line with paired saline", [[ACE_player, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;

// an inline blood warmer means the unit goes in warm.
if (([ACE_player, _target, "ACME_BloodWarmer"] call ACME_fnc_treatmentSupplyCount) >= 1) then {
    [_target, true] call ACME_fnc_bloodThermalStateCommit;
    ["Blood warmer inline.", 2, ACE_player] call ace_common_fnc_displayTextStructured;
};

// rebuild the menu, so both new rows and the decremented inventory counts show. it mirrors the close and reopen of
// addbag. the dialog is closed now, and the short delay lets it fully tear down and lets the ivbag attach events
// settle and sync, after which we retag the saline limb as the clamped y sentinel, ACME_SalineY, and reopen.
closeDialog 0;
[{
    params ["_patient", "_bp", "_iv", "_site"];
    if (isNull _patient) exitWith {};
    // retag the just-hung saline as the clamped y sentinel. it searches every body-part key rather than only the one
    // we expect, because if ACM stored it under a different key our single-key lookup would miss and never retag
    // it.
    private _bags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _done = false;
    {
        private _keyPart = _x;
        private _arr = _y;
        if (!_done) then {
            private _sIdx = _arr findIf { ((_x param [0, ""]) == "Saline") && {(_x param [4, true]) isEqualTo _iv} };
            if (_sIdx >= 0) then {
                private _e = +(_arr select _sIdx);
                _e set [0, "ACME_SalineY"];
                _arr set [_sIdx, _e];
                _bags set [_keyPart, _arr];
                [_patient, _bags] call ACME_fnc_ivBagsCommit;
                _done = true;
            };
        };
    } forEach _bags;
    [ACE_player, _patient, _bp] call ACM_circulation_fnc_openTransfusionMenu;
}, [_target, _bodyPart, _iv, _site], 0.3] call CBA_fnc_waitAndExecute;
