/* B287: one server-side owner ages deployed cooler cargo. */
if !(missionNamespace getVariable ["ACME_sys_bloodChain", true]) exitWith {};
if (!isServer) exitWith {};
private _spoilEnabled = missionNamespace getVariable ["ACME_bloodSpoilEnabled", true];
private _spoilT = missionNamespace getVariable ["ACME_bloodLooseSpoilTime", 1800];
private _now = serverTime;
private _boxes = (allMissionObjects "ACME_BloodCoolerBox_CSWB1U")
    + (allMissionObjects "ACME_BloodCoolerBox_CSWB2U")
    + (allMissionObjects "ACME_BloodCoolerBox_CSWB4U");
// Release from every box before any box acquires newly observed cargo. This
// makes box-to-box movement independent of enumeration order.
{[_x, _now, "release"] call ACME_fnc_coolerBoxReconcile;} forEach _boxes;
{
    private _box = _x;
    if (!(_box getVariable ["ACME_coolerPacking", false]) && {!(_box getVariable ["ACME_coolerRetired", false])}) then {
        private _state = [_box, _now] call ACME_fnc_coolerBoxReconcile;
        if !(_state isEqualTo []) then {
            private _kept = [];
            private _spoiled = [];
            {
                if (_spoilEnabled && {(_x # 1) >= _spoilT}) then {_spoiled pushBack (_x # 0);}
                else {_kept pushBack +_x;};
            } forEach (_state # 2);
            if !(_spoiled isEqualTo []) then {
                // Remove only expired blood; preserve every other cargo entry.
                {_box addItemCargoGlobal [_x, -1];} forEach _spoiled;
                _box addItemCargoGlobal ["ACME_SpoiledBlood", count _spoiled];
                _state set [2, _kept];
                _box setVariable ["ACME_boxCoolerState", _state, true];
                {
                    [format ["%1 blood unit(s) in a cooler lost the cold chain and spoiled.", count _spoiled], 3]
                        remoteExec ["ace_common_fnc_displayTextStructured", _x];
                } forEach (allPlayers select {(_x distance _box) < 12});
            };
        };
    };
} forEach _boxes;
