// opens ACM's own syringe-draw dialog, idd 84000, at the requested size, then injects our left-side syringe-size
// list and flushes list onto it once it exists. the size is baked into ACM's dialog at open, because its switch
// on _size sets the textures and the plunger limits, so switching size means re-opening at the new size, and this
// wrapper is what the size list calls back into.
// Args: size, patient, body part, optional flush item. A null patient opens a self draw.
params [["_size", 10], ["_patient", objNull], ["_bodyPart", ""], ["_flushClass", "", [""]]];
// A prefilled flush carries its own syringe and never requires an empty 10 mL item.
if (_flushClass != "") then {_size = 10;};
if (isNil "ACM_circulation_fnc_Syringe_Draw") exitWith {
    ["ACM syringe-draw isn't available.", 2, ACE_player] call ace_common_fnc_displayTextStructured;
};

// the narc box open sfx, only on a genuine open. a size switch, through skPickSize, stashes the mouse position
// into ACME_SK_RestoreMouse right before it closes and reopens at the new size, so a pending restore means a size
// switch and therefore a mute.
private _rmPending = uiNamespace getVariable ["ACME_SK_RestoreMouse", []];
if !((_rmPending isEqualType []) && {count _rmPending == 2}) then {
    // B60: every genuine new preparation starts with no tag; size-switch reopens preserve the current tag draft.
    uiNamespace setVariable ["ACME_SK_PendingTagColor", "none"];
    uiNamespace setVariable ["ACME_SK_PendingTagText", ["","",""]];
    playSound "ACME_NarcBoxOpen";
    // defensive: a genuine open clears any stale return-suppress flag so it can never carry over from a prior close
    // and wrongly suppress this session's return routing.
    uiNamespace setVariable ["ACME_SK_suppressReturn", false];
};

uiNamespace setVariable ["ACME_SK_CurSize", _size];
uiNamespace setVariable ["ACME_SK_Patient", _patient];
uiNamespace setVariable ["ACME_SK_BodyPart", _bodyPart];

// Keep the real return patient while native infusion drawing remains non-injectable.
private _infusion = !((missionNamespace getVariable ["ACME_infusion_pendingContext", []]) isEqualTo []);
ace_medical_gui_pendingReopen = false;
[ACE_player, if (_infusion) then {objNull} else {_patient}, _bodyPart, _size] call ACM_circulation_fnc_Syringe_Draw;

// wait for ACM's dialog to come up (its createdialog is one frame later), then inject.
[{
    params ["_args", "_h"];
    _args params ["_tries", "_flushClass"];
    if (!isNull (findDisplay 84000)) exitWith {
        [_h] call CBA_fnc_removePerFrameHandler;
        private _drawDisplayB51 = findDisplay 84000;
        private _barrel10B51 = _drawDisplayB51 displayCtrl 84012;
        if (!isNull _barrel10B51) then {
            // B51: the replacement artwork is the SALINE FLUSH barrel, not the generic 10 mL medication syringe.
            // Only a selected prefilled flush and the separate intubation cuff syringe use it.
            private _barrelTexture = if (_flushClass != "") then {
                "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa"
            } else {
                "\x\ACM\addons\circulation\ui\syringe\syringe_10_barrel_ca.paa"
            };
            _barrel10B51 ctrlSetText _barrelTexture;
        };
        call ACME_fnc_skInject;
        // B70 hard guarantee: create Select Syringe Tag immediately after the complete ACME control injection,
        // before compound/infusion mode setup can execute. The button is the FIRST control created by Ensure, so a
        // later setup script error can no longer leave the main syringe page without its selector. A second render
        // below repositions/repaints it after successful mode setup.
        private _tagDisplayEarly = findDisplay 84000;
        if (!isNull _tagDisplayEarly) then {
            _tagDisplayEarly setVariable ["ACME_SK_PendingTagReady", true];
            call ACME_fnc_skPendingTagEnsure;
            call ACME_fnc_skPendingTagRender;
        };
        // B121: reopening a running one-handed push must not initialize a fresh preparation session. The active
        // stable syringe already owns this dialog and its flow state lives outside every menu.
        private _hcPushOpen = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
        if (_hcPushOpen isEqualType createHashMap && {count _hcPushOpen > 0}) then {
            call ACME_fnc_hardcorePushRestoreUi;
        } else {
            // if an infusion bag context is pending, this draw is an INFUSION prep: repurpose the dialog's buttons
            // for "Inject Into Bag" (and set the infusion vial list + top text). re-applied here on every open AND
            // every size-switch reopen, so size switching stays in infusion mode. a plain narc-box draw has no
            // pending context and keeps the normal draw/push buttons.
            if !((missionNamespace getVariable ["ACME_infusion_pendingContext", []]) isEqualTo []) then {
                call ACME_fnc_patchDrawDialog;
            } else {
                // PLAIN narc-box draw: compounding is the DEFAULT.
                if (_flushClass != "" && {([ACE_player, _flushClass] call ACME_fnc_itemCount) > 0}) then {
                    [_flushClass] call ACME_fnc_skWasteBegin;
                } else {
                    if ((uiNamespace getVariable ["ACME_SK_WasteStage", ""]) == "") then {
                        [] call ACME_fnc_skCompoundBegin;
                    };
                };
            };
        };
        // Repaint after successful compound/flush/infusion setup. On the normal Narc Box path those routines do not
        // create controls, so the selector remains the topmost ACME control created after skInject.
        private _tagDisplay = findDisplay 84000;
        if (!isNull _tagDisplay) then {
            call ACME_fnc_skPendingTagEnsure;
            call ACME_fnc_skPendingTagRender;
        };
        // if this open came from a size switch, drop the cursor back where it was (skPickSize stashed it),
        // so switching syringe size doesn't fling the mouse to the screen edge.
        private _rm = uiNamespace getVariable ["ACME_SK_RestoreMouse", []];
        if (_rm isEqualType [] && {count _rm == 2}) then {
            setMousePosition _rm;
            uiNamespace setVariable ["ACME_SK_RestoreMouse", []];
        };
    };
    _args set [0, _tries + 1];
    if (_tries > 90) then { [_h] call CBA_fnc_removePerFrameHandler; };  // give up after about 1.5 s.
}, 0, [0, _flushClass]] call CBA_fnc_addPerFrameHandler;
