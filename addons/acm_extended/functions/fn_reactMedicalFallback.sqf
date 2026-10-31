/* Browser commands navigate to the real native workflow; never debit items or toggle flow here. */
params ["_display",["_route",[],[[]]]];
if (isNull _display || {!(_display isEqualTo findDisplay 89300)}) exitWith {false};
private _context = _display getVariable ["ACME_reactContext",[]];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {_display closeDisplay 0;false};
private _serial = _display getVariable ["ACME_reactSerial",-1];
private _part = _context select 2;
private _returnAccess = +(_context select 3);
if (count _route == 3) then {
    _part = _route select 0;
    _returnAccess = [_route select 1,_route select 2];
};
_display closeDisplay 0;
[{
    params ["_context","_serial","_part","_returnAccess"];
    // A newer browser or unrelated dialog must never be closed by this old handoff.
    if (dialog || {_serial != (missionNamespace getVariable ["ACME_reactSerial",-2])}
        || {!([_context] call ACME_fnc_reactMedicalValid)}) exitWith {};
    private _patient = _context select 1;
    if (count _returnAccess == 2 && {!([_patient,_part,_returnAccess select 0,_returnAccess select 1] call ACME_fnc_transfusionAccessValid)}) exitWith {};
    [_context select 0,_patient,_part,_returnAccess,true] call ACM_circulation_fnc_openTransfusionMenu;
},[_context,_serial,_part,_returnAccess],0] call CBA_fnc_waitAndExecute;
true
