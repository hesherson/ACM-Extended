/* B275: read the downstream device on this exact IV/IO. Fitting/removal belongs
 * to lineWarmerCommit, after the provider has reserved one physical warmer.
 * Old hang callers may still pass _fit; possession alone never creates equipment. */
params ["_patient", "_part", "_iv", "_site"];
if (isNull _patient) exitWith {false};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _lines = _patient getVariable ["ACME_lineWarmers", createHashMap];
(_lines getOrDefault [_key, false]) isEqualTo true
