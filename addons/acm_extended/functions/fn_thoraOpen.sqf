// open the thoracostomy mini-game, idd 86600. it mirrors fn_chestsealopen: stash the medic and patient on
// uinamespace, then createdialog after a short beat, and after lowering an elevated head, the same as the chest
// seal.
// call it as [_medic, _patient, _bodyPart] call ACME_fnc_thoraOpen.
params ["_medic", "_patient", ["_bodyPart", ""]];
if (isNull _patient || {isNull _medic}) exitWith {};
if !([_medic, _patient] call ACME_fnc_thoraCanOpen) exitWith {};

// Thoracostomy becomes the sole modal UI owner before any remote casualty preparation starts. Suppress ACE's
// treatment-success menu reopen and retire the old menu PFH now; otherwise a late ACE closeDialog can destroy
// the thoracostomy dialog on the frame it appears.
ace_medical_gui_pendingReopen = false;
call ACM_GUI_fnc_pauseMedicalMenuPFH;
private _medicalMenu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
if (!isNull _medicalMenu) then {_medicalMenu closeDisplay 2;};
private _ecgJostleKey = "ui:thora:" + str clientOwner;
[_patient, _ecgJostleKey, true] call ACME_fnc_ecgJostleRequest;

uiNamespace setVariable ["ACME_Thora_Medic", _medic];
uiNamespace setVariable ["ACME_Thora_Patient", _patient];
uiNamespace setVariable ["ACME_Thora_BodyPart", _bodyPart];

// Hold an identified chest-access gear lease for the entire minigame. It is independent from head elevation: a
// backpack-supported casualty still has the worn plate carrier parked above the head until this screen closes.
private _vestSerial = (uiNamespace getVariable ["ACME_Thora_ChestAccessSerial",0]) + 1;
uiNamespace setVariable ["ACME_Thora_ChestAccessSerial",_vestSerial];
private _vestLease = format ["thora:%1:%2:%3",clientOwner,floor(CBA_missionTime*1000),_vestSerial];
uiNamespace setVariable ["ACME_Thora_ChestAccessLease",_vestLease];
[_patient,_medic,_vestLease,true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;

// The chest-access lease now owns Semi-Fowler lowering plus any lift/remove/park/lower carrier choreography.
// Open the thoracostomy UI only after that patient-side transaction is genuinely ready.
private _open = {
    params ["_p","_m","_lease"];
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease",""]) != _lease) exitWith {};
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m}) exitWith {
        // No display exists yet, but fn_thoraClose is also the authoritative pre-open abort cleanup: it releases
        // the exact chest-access lease, restores the medical-menu lifecycle and clears ECG jostle state.
        [] call ACME_fnc_thoraClose;
    };

    ["ACME_Thoracostomy_Dialog"] call ACME_fnc_minigameOpen;

    [{
        params ["_p","_m","_lease"];
        if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease",""]) != _lease) exitWith {};
        if (isNull (findDisplay 86600)) then {
            // createDialog failed or another UI closed us before onLoad. Run the same cleanup as a normal close so
            // the provider is never stranded in chest-access theatre with the medical menu disabled.
            [] call ACME_fnc_thoraClose;
        };
    }, [_p,_m,_lease], 0.25] call CBA_fnc_waitAndExecute;
};

[{
    params ["_p","_m","_lease"];
    if (isNull _p || {isNull _m} || {!alive _m}
        || {(uiNamespace getVariable ["ACME_Thora_ChestAccessLease",""]) != _lease}) exitWith {true};
    private _readyLease = _p getVariable ["ACME_chestAccess_readyLease",""];
    private _ready = _p getVariable ["ACME_chestAccess_readyServer",-1];
    (_readyLease == _lease) && {_ready isEqualType 0} && {_ready >= 0} && {serverTime >= _ready}
}, _open, [_patient,_medic,_vestLease], 12, {
    params ["_p","_m","_lease"];
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease",""]) != _lease) exitWith {};
    diag_log format ["[ACME THORACOSTOMY] Chest-access preparation timed out on %1.", netId _p];
    [] call ACME_fnc_thoraClose;
}] call CBA_fnc_waitUntilAndExecute;
