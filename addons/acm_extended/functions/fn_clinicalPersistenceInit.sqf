/* A netId identifies a live object only within this mission incarnation.
 * Publish once from the server; clients never invent competing incarnations.
 * This is an identity fence, not a secret or an authentication credential. */
if (isServer && {isNil "ACME_clinicalPersistenceSession"}) then {
    private _session = format ["ACME-%1-%2-%3", systemTimeUTC, floor random 1000000000, diag_tickTime];
    missionNamespace setVariable ["ACME_clinicalPersistenceSession", _session, true];
};
true
