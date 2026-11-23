/* Open the Megacode instructor panel on a validated Kelly target. */
params [["_target",objNull,[objNull]], ["_caller",objNull,[objNull]]];
if (isNull _caller) then {_caller=ACE_player;};
if (isNull _target || {!(_target getVariable ["ACME_isMegacode",false])}) exitWith {
    diag_log "[ACME][Megacode] Refused panel open: invalid manikin target";
    if (!isNull _caller) then {["Megacode station has no valid manikin target.",2.5,_caller] call ace_common_fnc_displayTextStructured;};
};
if (!hasInterface) exitWith {};

// Already open on this manikin: nothing to do. (An exitWith inside the "then" block below only left that block, so
// a second Open on the same manikin, e.g. the AAR action, stacked a second panel and a second monitor PFH.)
private _existing = uiNamespace getVariable ["ACME_Megacode_DLG",displayNull];
if (!isNull _existing && {(uiNamespace getVariable ["ACME_MC_target",objNull]) isEqualTo _target}) exitWith {};
if (!isNull _existing) then {closeDialog 0;};
uiNamespace setVariable ["ACME_MC_target",_target];
uiNamespace setVariable ["ACME_MC_operator",_caller];
_target setVariable ["ACME_MC_operatorClient",_caller,true];

private _ok = createDialog "ACME_Megacode_Panel";
if (!_ok) exitWith {
    diag_log "[ACME][Megacode] createDialog ACME_Megacode_Panel failed";
    if (!isNull _caller) then {["Megacode panel failed to open. Check RPT for ACME config/UI errors.",3,_caller] call ace_common_fnc_displayTextStructured;};
};

// Gesture starts only after the dialog actually exists, so a config/UI failure can never strand the operator.
private _tok=(_caller getVariable ["ACME_MC_animTok",0])+1;
_caller setVariable ["ACME_MC_animTok",_tok,false];
[_caller,"Acts_Kore_TalkingOverRadio_in"] call ACME_fnc_doAnim;
[{
    params ["_op","_t"];
    if (isNull _op || {(_op getVariable ["ACME_MC_animTok",-1]) != _t}) exitWith {};
    if (isNull (uiNamespace getVariable ["ACME_Megacode_DLG",displayNull])) exitWith {};
    [_op,"Acts_Kore_TalkingOverRadio_loop"] call ACME_fnc_doAnim;
},[_caller,_tok],missionNamespace getVariable ["ACME_megacode_animInTime",1.6]] call CBA_fnc_waitAndExecute;
