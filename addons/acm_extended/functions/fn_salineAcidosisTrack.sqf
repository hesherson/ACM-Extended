/* NA3. Actual normal-saline intake is committed in the owner drainer/flush endpoint. This only clears burden. */
{
    private _p = _x;
    if (!local _p || {!alive _p}) then {continue;};
    private _dt = [_p, "salineClear", 0.25, 5] call ACME_fnc_clinicalTickDelta;
    private _burden = _p getVariable ["ACME_circ_salineGivenMl", 0];
    if (_burden <= 0) then {continue;};
    if ((missionNamespace getVariable ["ACME_salineAcidosis_enabled", true]) && {missionNamespace getVariable ["ACME_salineAcidosis_decayMatchesACM", true]}) then {
        private _rate = missionNamespace getVariable ["ACME_salineAcidosis_clearMlPerSec", 0.7];
        // Match the native drainer threshold in overrides/fn_getBloodVolumeChange.sqf.
        private _fresh = _p getVariable ["ACM_circulation_IV_Bags_FreshBloodEffect", 0];
        private _mod = [1,2] select (_fresh > 0.83);
        [_p, "ACME_circ_salineGivenMl", (_burden - (_rate * _mod * _dt)) max 0, 5, 1] call ACME_fnc_setVarNetApprox;
    };
} forEach ((missionNamespace getVariable ["ACME_circ_activePatients", []]) select {(_x getVariable ["ACME_circ_salineGivenMl", 0]) > 0});
