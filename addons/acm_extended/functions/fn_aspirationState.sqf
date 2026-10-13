/* Read-only atomic aspiration authority: [clinical epoch, processed key, load, edema, explicit serial high-water].
 * Scalar mirrors never reconstruct authority after locality transfer. A missing packet with nonzero mirrors defers.
 */
params ["_patient"];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
if !(_epoch isEqualType 0 && {finite _epoch} && {_epoch >= 0} && {_epoch == floor _epoch}) exitWith {[]};
private _state = _patient getVariable ["ACME_aspiration_State", []];
if (_state isEqualTo []) exitWith {
    private _load = _patient getVariable ["ACME_aspiration_load",0];
    private _edema = _patient getVariable ["ACME_aspiration_edema",0];
    if !(_load isEqualType 0 && {finite _load} && {_edema isEqualType 0} && {finite _edema}) exitWith {[]};
    if (_load != 0 || {_edema != 0}) then {[]} else {[_epoch,"",0,0,0]}
};
if !(_state isEqualType [] && {count _state == 5}) exitWith {[]};
_state params ["_bound","_key","_load","_edema","_serial"];
if !(_bound isEqualType 0 && {finite _bound} && {_bound >= 0} && {_bound == floor _bound} && {_key isEqualType ""}
    && {_load isEqualType 0} && {finite _load} && {_load >= 0 && {_load <= 1}}
    && {_edema isEqualType 0} && {finite _edema} && {_edema >= 0 && {_edema <= 1}}
    && {_serial isEqualType 0} && {finite _serial} && {_serial >= 0} && {_serial == floor _serial}) exitWith {[]};
if (_bound != _epoch) exitWith {[_epoch,"",0,0,0]};
+_state
