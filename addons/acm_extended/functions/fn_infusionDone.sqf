/* Done is the only Prep Infusion completion action.
 * Medication is committed when Inject Into Bag succeeds. Done confirms that settled mixture and returns to
 * Transfuse; it never silently accepts an in-flight injection or medication still sitting in the syringe. */
disableSerialization;
private _display = findDisplay 84000;
if (isNull _display) exitWith {};
private _context = missionNamespace getVariable ["ACME_infusion_pendingContext", []];
if (_context isEqualTo []) exitWith {};

// An active-bag injection is owner-authoritative and acknowledged asynchronously. Closing before the ACK makes the
// operator think Done confirmed a dose which may still be rejected and refunded a frame later.
if ((missionNamespace getVariable ["ACME_infusion_pendingInject", ""]) != "") exitWith {
    [ACE_player, "Wait for the current injection to finish confirming before pressing Done."] call ACME_fnc_clinicalNotice;
};

// A pulled plunger is only a proposed dose. Supplies are not consumed until Inject Into Bag succeeds. Do not let
// Done make an un-injected syringe look as though it became part of the bag mixture.
private _drawn = missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0];
private _moving = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving", false];
if (_moving || {_drawn > 0.0005}) exitWith {
    [ACE_player, "Medication is still in the syringe. Inject it into the bag or return the plunger to 0 mL before pressing Done."] call ACME_fnc_clinicalNotice;
};

private _confirmedRows = [];
if ((_context param [0, ""]) == "prepared") then {
    private _sid = _context param [20, ""];
    private _entries = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
    private _idx = _entries findIf {(_x param [0, ""]) == _sid};
    if (_idx >= 0) then {_confirmedRows = [_entries select _idx] call ACME_fnc_preparedComponents;};
} else {
    private _patient = _context param [1, objNull];
    private _bagId = _context param [21, ""];
    if (!isNull _patient && {_bagId != ""}) then {
        {
            if ((_x param [23, ""]) == _bagId) then {
                private _med = _x param [11, ""];
                private _dose = _x param [13, 0];
                private _count = _x param [27, 1];
                private _ri = _confirmedRows findIf {(_x param [0, ""]) == _med};
                if (_ri < 0) then {_confirmedRows pushBack [_med, _dose, _count];} else {
                    private _r = +(_confirmedRows select _ri);
                    _r set [1, (_r param [1, 0]) + _dose];
                    _r set [2, (_r param [2, 0]) + _count];
                    _confirmedRows set [_ri, _r];
                };
            };
        } forEach (_patient getVariable ["ACME_infusion_BagMedications", []]);
    };
};

if !(_confirmedRows isEqualTo []) then {
    private _parts = _confirmedRows apply {
        _x params ["_med", "_dose"];
        format ["%1 %2", _med, [_med, _dose] call ACME_fnc_formatDose]
    };
    [ACE_player, format ["Infusion bag confirmed: %1", _parts joinString ", "]] call ACME_fnc_clinicalNotice;
};

private _return = _display getVariable ["ACME_SK_Return", []];
uiNamespace setVariable ["ACME_SK_suppressReturn", true];
ace_medical_gui_pendingReopen = false;
// The prepared bag now owns the mixture. The transient syringe-into-bag context must die BEFORE the display
// unload/reopen sequence or a fast page change can inherit it and force a normal Narc Box back into infusion view.
ACME_infusion_pendingContext = nil;
missionNamespace setVariable ["ACME_infusion_bagTally", []];
_display closeDisplay 2;
if !(_return isEqualTo []) then {
    [{[_this] call ACME_fnc_reopenTransfusion;}, _return, 0.05] call CBA_fnc_waitAndExecute;
};
