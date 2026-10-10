/* Stable B182: return true only when a live ACME provider controller deliberately owns unit animation speed.
 *
 * This is intentionally narrower than providerStanceOwned. Menu crouch, Direct Pressure and other stance owners
 * must not prevent an old accelerated treatment from restoring getAnimSpeedCoef to 1.
 *
 * _ignoreRemoteEpoch lets treatmentPoseSync retire its own exit record while checking for a newer speed owner.
 */
params [
    ["_unit", objNull, [objNull]],
    ["_ignoreRemoteEpoch", -1, [0]]
];

if (isNull _unit) exitWith {false};
// B213: the finite pressure release owns speed/stance only on its originating locality.
private _pressureExit = _unit getVariable ["ACME_DP_Exit", []];
if ((count _pressureExit) >= 7
    && {(_pressureExit param [2, -1]) == (_unit getVariable ["ACME_providerLocalityEpoch", 0])}
    && {(CBA_missionTime - (_pressureExit param [4, -1e6])) < ((_pressureExit param [6, 0]) + 2)}) exitWith {true};

if ((_unit getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []) exitWith {true};
if ((_unit getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []) exitWith {true};
if (_unit getVariable ["ACME_headElev_seqActive", false]) exitWith {true};

private _remote = _unit getVariable ["ACME_treatmentPoseRemote", []];
private _remoteEpoch = _remote param [0, -1];
private _remoteOp = _remote param [1, ""];
private _remoteOwns = false;

if (_remoteEpoch >= 0 && {_remoteEpoch != _ignoreRemoteEpoch} && {_remoteOp in ["run", "hold", "exit"]}) then {
    private _episode = _unit getVariable ["ACME_treatmentPoseEpisode", [-1, false]];
    private _episodeEpoch = _episode param [0, -1];
    private _episodeLive = _episode param [1, false];

    if (_remoteOp in ["run", "hold"]) then {
        _remoteOwns = _episodeEpoch == _remoteEpoch && {_episodeLive};
    } else {
        if (_remoteOp == "exit") then {
            _remoteOwns = _episodeEpoch == _remoteEpoch;
        };
    };
};

_remoteOwns
