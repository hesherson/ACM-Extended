/* B14: all hypnotics use induction-normalized load (1 = configured induction).
   Native analgesia is separate. An opioid is an adjunct, never a stand-alone hypnotic.
   Keep the six-field contract used by the debug/airway readers. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!alive _patient}) exitWith {[0,0,0,0,1,0]};
private _ket = ([_patient] call ACME_fnc_ketamineOnBoard)
    / ((missionNamespace getVariable ["ACME_ket_induceThreshold", 7]) max 0.1);
private _prop = [_patient] call ACME_fnc_propofolOnBoard;
private _midIV = [_patient, "Midazolam_IV", false] call ACME_fnc_medicationCountCompat;
private _midIM = [_patient, "Midazolam", false] call ACME_fnc_medicationCountCompat;
private _mid = ((_midIV max 0) * 0.5 + (_midIM max 0) * 0.65)
    * ((missionNamespace getVariable ["ACME_sedation_midazolamEquiv", 1]) max 0);
private _fent = [_patient] call ACME_fnc_fentanylOnBoard;
// B38: morphine can also augment a hypnotic. Native route/effect counts already
// include absorption and washout; do not substitute inventory mg or bag contents.
private _morphine = 0;
{
    private _value = [_patient, _x, false] call ACME_fnc_medicationCountCompat;
    if (_value isEqualType 0 && {finite _value}) then {_morphine = _morphine + (_value max 0 min 16);};
} forEach ["Morphine", "Morphine_IV"];
private _opioidAdjunct = (_fent + 0.5 * _morphine) min 1;
private _factor = 1 + _opioidAdjunct * ((missionNamespace getVariable ["ACME_sedation_fentanylAdjunct", 0.35]) max 0 min 1);
// Propofol and midazolam potentiate each other's hypnosis. The cross term is
// bounded and vanishes when either drug wears off; opioids alone remain analgesic.
private _propMid = (_prop min 16) * (_mid min 16);
private _hypnoticSynergy = 0.25 * (_propMid / (0.5 + _propMid));
[_ket, _prop, _mid, _fent, _factor, (_ket + _prop + _mid + _hypnoticSynergy) * _factor]
