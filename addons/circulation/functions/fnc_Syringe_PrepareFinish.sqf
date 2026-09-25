/* B19: exact-volume vial consumption. A physical vial becomes an invisible open-vial balance after first puncture. */
params ["_medic", "_medication", "_dose", ["_size", 10]];
if (isNull _medic || {_medication == ""} || {_dose <= 0} || {!finite _dose}) exitWith {false};
// Filled magazines store hundredths of a milliliter. Debit that same amount,
// rather than losing the fraction that was previously floored only at storage.
_dose = (round (_dose * 100)) / 100;
if (_dose <= 0 || {!(_size in [1,3,5,10])} || {_dose > _size + 0.001}) exitWith {false};
private _holder = [_medic] call ACME_fnc_vialHolder;
if (isNull _holder) exitWith {false};
// B25: the source ledger may contain many identical vials, but the active syringe may only consume vials the
// provider deliberately unlocked in this draw session. This prevents a 10 mL syringe from silently draining ten
// separate 1 mL epinephrine vials in one pull.
private _dlgVial = findDisplay 84000;
private _sessionOK = true;
if (!isNull _dlgVial) then {
    private _unlocked = ["limit", _medication, _dose, _dlgVial] call ACME_fnc_vialSession;
    if (_dose > _unlocked + 0.0005) then {_sessionOK = false;};
};
if (!_sessionOK) exitWith {false};
private _empty = format ["ACM_Syringe_%1", _size];
if !([_medic,[[_medication,_dose]],_empty,true] call ACME_fnc_medicationTakeSources) exitWith {false};
[_medic, format ["ACM_Syringe_%1_%2", _size, _medication], "", round (_dose * 100)] call ace_common_fnc_addToInventory;
private _dlgB25 = findDisplay 84000; if (!isNull _dlgB25) then {["clear", "", 0, _dlgB25] call ACME_fnc_vialSession;};

// A successful draw returns the plunger to an empty-syringe state. Push/inject and infusion prep retain their state.
if ((missionNamespace getVariable ["ACME_lastSyringeBtnType", -1]) == 0
    && {(missionNamespace getVariable ["ACME_infusion_pendingContext", []]) isEqualTo []}) then {
    private _dlg = findDisplay 84000;
    if (!isNull _dlg) then {
        private _top = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop", -1];
        if (_top >= 0) then {
            private _plunger = _dlg displayCtrl 84009;
            if (!isNull _plunger) then {
                (ctrlPosition _plunger) params ["_px", "", "_pw", "_ph"];
                _plunger ctrlSetPosition [_px, _top, _pw, _ph];
                _plunger ctrlCommit 0;
            };
            private _vis = _dlg displayCtrl (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerVisual", -1]);
            if (!isNull _vis) then {
                private _adj = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment", 0];
                (ctrlPosition _vis) params ["_vx", "", "_vw", "_vh"];
                _vis ctrlSetPosition [_vx, (_top - _adj), _vw, _vh];
                _vis ctrlCommit 0;
            };
            ACM_circulation_SyringeDraw_DrawnAmount = 0;
            ACM_circulation_SyringeDraw_Moving = false;
        };
    };
};
true
