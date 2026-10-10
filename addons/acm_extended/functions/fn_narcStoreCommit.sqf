/* Provider-owner writer for the persistent Narc Box syringe/medication store.
 * Live Hardcore plunger steps and rejected-dose corrections stay local; final settlement
 * publishes the reconciled store once. Never broadcast the 20 Hz plunger updates.
 */
params ["_owner", "_store", ["_public", true, [true]]];
if (isNull _owner || {!local _owner}) exitWith {false};
_owner setVariable ["ACME_narcStore", _store, _public];
true
