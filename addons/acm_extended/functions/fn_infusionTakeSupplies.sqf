/* Reserve Prep Infusion source solution through the same exact-volume source transaction used by the Narc Box.
 * The selected medication key and mL are already bound by the syringe dialog; this helper validates the complete
 * debit first, consumes that exact medication/volume, and handles reusable-syringe rules without a parallel path.
 */
params ["_medic", "_med", "_ml", "_size"];
if (!local _medic || {_med == ""} || {_ml <= 0} || {!finite _ml} || {!(_size in [1,3,5,10])} || {_ml > _size + 0.001}) exitWith {[]};

private _syringe = format ["ACM_Syringe_%1", _size];
private _reusable = missionNamespace getVariable ["ACM_circulation_reusableSyringe", false];

// ACME_fnc_medicationTakeSources is the Narc Box's validated exact-source debit. A one-component batch is
// therefore the same transaction for Prep Infusion, with no guessed classname and no second medication ledger.
private _patient = (missionNamespace getVariable ["ACME_infusion_pendingContext",[]]) param [1,objNull];
// The receipt captures the vial holder and container donor independently. ACKs
// can settle it after the source selector changes or its UI lease is released.
[_medic, [[_med, _ml]], _syringe, !_reusable, true, _patient] call ACME_fnc_medicationTakeSources
