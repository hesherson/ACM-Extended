/*
 * (Re)build the cable between a Megacode Kelly manikin and its laptop, on the server.
 *
 * The cable is an engine rope between two hidden rope helpers. A rope whose ends hang on attached objects stays
 * where it was made (it does not follow a later move of the laptop or of the anchors), so every change of the
 * laptop or of an anchor tears the whole cable down and makes it again here.
 *
 * Laptop end: Land_Laptop_03_olive_F, measured from its game model (geometry LOD, model axes x right, y forward,
 * z up): base x -0.177..0.178, y -0.135..0.157, z -0.167..-0.128; the screen stands at the back, y 0.134..0.157,
 * z -0.128..0.162. The spawn turns the laptop round, so its +y (the back, behind the screen) faces the manikin.
 * The port is on the back face of the base, right of centre, at mid height of the base:
 * ACME_megacode_laptopHoseOffset [0.10, 0.152, -0.143]. A plug (ACME_MegacodePlug) sits on it, pointing out along
 * +y, and the rope is anchored ACME_megacode_plugLength (0.036 m) out along the plug, a few millimetres inside the
 * plug's tail (which ends at 0.042), so the cable comes out of the plug instead of hanging in the air.
 * Manikin end: ACME_megacode_dummyHoseOffset on the manikin.
 * B395: "make the megacode kelly cable have a couple bends in it to look like a more natural cable. it should still be
 * the physics enabled cable": the cable runs through two hidden points on the ground, a third and two thirds of
 * the way, set off to either side of the straight line (ACME_megacode_cableBends: [share of the way, sideways m]),
 * so it lies in an S; it is three physics ropes meeting at those points, each with a little slack.
 *
 * Arguments: 0 the manikin. Returns the rope (or objNull when it could not be made).
 */
params [["_u", objNull, [objNull]]];
if (!isServer || {isNull _u}) exitWith {objNull};
private _laptop = _u getVariable ["ACME_MC_laptop", objNull];

// tear down the old cable, the plug included.
{if (!isNull _x) then {ropeDestroy _x;};} forEach ((_u getVariable ["ACME_MC_ropes", []]) + [_u getVariable ["ACME_MC_rope", objNull]]);
_u setVariable ["ACME_MC_ropes", [], false];
{if (!isNull _x) then {deleteVehicle _x;};} forEach (_u getVariable ["ACME_MC_helpers", []]);
_u setVariable ["ACME_MC_rope", objNull, false];
_u setVariable ["ACME_MC_helpers", [], false];
if (isNull _laptop) exitWith {objNull};

private _port = +(missionNamespace getVariable ["ACME_megacode_laptopHoseOffset", [0.10, 0.152, -0.143]]);
private _plugLen = missionNamespace getVariable ["ACME_megacode_plugLength", 0.036];
private _tip = _port vectorAdd [0, _plugLen, 0];
private _dHose = +(missionNamespace getVariable ["ACME_megacode_dummyHoseOffset", [0, 0.32, 0.12]]);
private _slack = missionNamespace getVariable ["ACME_megacode_ropeSlack", 0.2];
private _segN = missionNamespace getVariable ["ACME_megacode_ropeSegments", 0];

// the plug, on the port, turned with the laptop (an attached object keeps the parent's axes, so it points out of
// the back face with no turning of its own, which would not reach other machines reliably).
private _plug = createVehicle ["ACME_MegacodePlug", [0, 0, 0], [], 0, "CAN_COLLIDE"];
_plug allowDamage false;
_plug setPosWorld (_laptop modelToWorldWorld _port);
_plug attachTo [_laptop, _port];
_plug disableCollisionWith _laptop;

// rope-capable, hidden helpers at both ends (ropeCreate needs physics objects at both ends). each is put on its
// spot before it is attached, so the rope made in this same frame starts where it belongs.
private _lHelper = createVehicle ["ace_fastroping_helper", [0, 0, 0], [], 0, "CAN_COLLIDE"];
private _dHelper = createVehicle ["ace_fastroping_helper", [0, 0, 0], [], 0, "CAN_COLLIDE"];
{
    _x allowDamage false;
    _x hideObjectGlobal true;
    _x enableRopeAttach true;
} forEach [_lHelper, _dHelper];
_lHelper setPosWorld (_laptop modelToWorldWorld _tip);
_lHelper attachTo [_laptop, _tip];
_dHelper setPosWorld (_u modelToWorldWorld _dHose);
_dHelper attachTo [_u, _dHose];
_lHelper disableCollisionWith _laptop;
_lHelper disableCollisionWith _plug;
_dHelper disableCollisionWith _u;
_dHelper disableCollisionWith _lHelper;

// the bend points: on the ground between the two ends, off to the sides of the straight line.
private _from = _laptop modelToWorldWorld _tip;
private _to = _u modelToWorldWorld _dHose;
private _flat = [(_to select 0) - (_from select 0), (_to select 1) - (_from select 1), 0];
private _side = if ((vectorMagnitude _flat) > 0.01) then {(vectorNormalized _flat) vectorCrossProduct [0, 0, 1]} else {[1, 0, 0]};
private _points = [_lHelper];
private _bendHelpers = [];
if ((_from distance2D _to) > 0.8) then {
    {
        _x params ["_share", "_off"];
        private _p = (_from vectorAdd ((_to vectorDiff _from) vectorMultiply _share)) vectorAdd (_side vectorMultiply _off);
        private _h = createVehicle ["ace_fastroping_helper", [0, 0, 0], [], 0, "CAN_COLLIDE"];
        _h allowDamage false;
        _h hideObjectGlobal true;
        _h enableRopeAttach true;
        _h setPosASL [_p select 0, _p select 1, (getTerrainHeightASL _p) + 0.015];
        _h enableSimulationGlobal false;  // a fixed point the cable lies round
        {_h disableCollisionWith _x;} forEach [_laptop, _u, _plug, _lHelper, _dHelper];
        _points pushBack _h;
        _bendHelpers pushBack _h;
    } forEach (missionNamespace getVariable ["ACME_megacode_cableBends", [[0.34, 0.22], [0.68, -0.18]]]);
};
_points pushBack _dHelper;

// biki ropeCreate: [from, fromPoint, to, toPoint, length, ropeStart, ropeEnd, ropeType, nSegments]; nSegments is
// the 9th argument (engine maximum 63). Each piece anchors at the helper origins (the laptop end inside the plug);
// its length is the straight span plus a share of the slack, so it sags and curls a little.
private _ropes = [];
private _pieces = (count _points) - 1;
for "_i" from 0 to (_pieces - 1) do {
    private _a = _points select _i;
    private _b = _points select (_i + 1);
    private _len = (((getPosWorld _a) distance (getPosWorld _b)) max 0.2) * 1.08 + (_slack / _pieces);
    private _segs = if (_segN >= 1) then {(round (_segN / _pieces)) max 4} else {(round (_len / 0.04)) max 6};
    private _rope = objNull;
    {
        if (isNull _rope) then {_rope = ropeCreate [_a, [0, 0, 0], _b, [0, 0, 0], _len, [], [], _x, _segs min 63];};
    } forEach [missionNamespace getVariable ["ACME_megacode_ropeClass", "ACME_MegacodeCable_Rope"], "ace_refuel_fuelHose"];
    if (isNull _rope) then {_rope = ropeCreate [_a, [0, 0, 0], _b, [0, 0, 0], _len];};  // the engine-default fallback.
    _ropes pushBack _rope;
};
private _rope = _ropes param [0, objNull];
_u setVariable ["ACME_MC_ropes", _ropes, false];
_u setVariable ["ACME_MC_rope", _rope, false];
_u setVariable ["ACME_MC_helpers", [_dHelper, _lHelper, _plug] + _bendHelpers, false];
// published for checks and the debug tuner: where the laptop end of the cable is, in the laptop's model axes.
_laptop setVariable ["ACME_MC_cablePort", [_port, _tip], true];
_rope
