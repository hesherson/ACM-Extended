// the spaced MODE title for the top bar of the live screen.
// the device prints the ventilation mode across the full width of its title strip, so "SIMV VC PS" reads as three
// widely separated tokens rather than a short phrase huddled in the middle.
// widening the gaps is the whole trick: the glyphs are untouched and only the spaces between words grow, so the text
// stays the same size and weight as every other title on the machine.
// it is applied at display time only. the stored mode string, ACME_vent_mode, keeps its normal single spaces,
// because every comparison in the vent code matches on it exactly, such as "CPAP PS HF" and "IMV VC (CPR)", and
// padding the stored value would break all of them.
// call it as ["SIMV VC PS"] call ACME_fnc_ventModeTitle, which returns "SIMV   VC   PS".

params [["_mode", "SIMV VC PS"]];
if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])})) exitWith { "SIMPLE" };
if !(_mode isEqualType "") exitWith { "" };

private _gap = missionNamespace getVariable ["ACME_vent_modeTitleGap", 3];
private _pad = "";
for "_i" from 1 to (_gap max 1) do { _pad = _pad + " "; };

private _words = (_mode splitString " ") select {_x != ""};
if (_words isEqualTo []) exitWith { _mode };

private _out = _words select 0;
for "_i" from 1 to ((count _words) - 1) do {
    _out = _out + _pad + (_words select _i);
};
_out
