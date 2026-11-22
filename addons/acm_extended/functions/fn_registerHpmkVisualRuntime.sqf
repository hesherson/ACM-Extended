/*
 * Phase 24 subsystem ownership: HPMK blanket reconciliation, pickup interaction and client visual runtime.
 *
 * Extracted intact from ACME_fnc_postInit and invoked at the original point so startup
 * sequencing and CBA registration order are preserved.
 */

// Server-side HPMK safety reconciliation uses an explicit registry; no recurring allUnits scan.
if (isServer) then {
    ACME_hpmk_serverPatients = allUnits select {
        (_x getVariable ["ACME_hpmk_state", ""]) != ""
            || {!isNull (_x getVariable ["ACME_hpmk_blanket", objNull])}
    };
    ["ACME_hpmkServerTrack", {
        params [["_patient", objNull, [objNull]], ["_state", "", [""]]];
        if (isNull _patient) exitWith {};
        if (_state == "" && {isNull (_patient getVariable ["ACME_hpmk_blanket", objNull])}) then {
            ACME_hpmk_serverPatients = ACME_hpmk_serverPatients - [_patient];
        } else {
            ACME_hpmk_serverPatients pushBackUnique _patient;
        };
    }] call CBA_fnc_addEventHandler;
};
[{call ACME_fnc_hpmkBlanketTick}, 2, []] call CBA_fnc_addPerFrameHandler;

// the "Pick Up HPMK" ACE object interaction on a dropped blanket, shed when a wrapped patient got up. it
// registers per client, through addactiontoclass with a hasinterface guard inside createaction, and gates on
// ACME_hpmk_dropped. it therefore shows on our dropped blankets only, not on map clutter of the same class.
// execnextframe runs it after ACE's interact_menu is initialized. if ACME_hpmk_blanketClass is retuned, move
// this to the new class.
if (hasInterface) then {
    [{
        if (isNil "ace_interact_menu_fnc_createAction") exitWith {};
        private _act = [
            "ACME_PickUpHPMK",
            "Pick Up HPMK",
            "\acm_extended\ui\items\HPMK_ca.paa",
            { [_target, _player] call ACME_fnc_hpmkPickUp; },
            { _target getVariable ["ACME_hpmk_dropped", false] }
        ] call ace_interact_menu_fnc_createAction;
        // the interaction now lives on the collision-free anchor, Land_HelipadEmpty_F, and not on the blanket prop,
        // because the blanket prop no longer exists as a networked object. it is a client-side simple object with no
        // collision. it gates on ACME_hpmk_dropped, so an ordinary helipad never shows this.
        // (under ACE's main node, with "Rotate towards me" of acme_equipment: two nodes of their own would lie on
        // one spot)
        ["Land_HelipadEmpty_F", 0, ["ACE_MainActions"], _act] call ace_interact_menu_fnc_addActionToClass;
    }] call CBA_fnc_execNextFrame;
};


// HPMK blanket visuals, client-side.
// These display meshes never participate in gameplay physics or modify a patient's gear or position.
if (hasInterface) then {
    ACME_hpmk_visuals = createHashMap;         // dropped anchor netId -> local simple object
    [{
        private _class = missionNamespace getVariable ["ACME_hpmk_blanketClass", ""];
        private _feature = missionNamespace getVariable ["ACME_sys_hpmk", true];

        // Dropped world blankets: reconcile from network anchors.
        private _seenDrop = [];
        if (_feature && {_class != ""}) then {
            {
                private _anchor = _x;
                private _id = netId _anchor;
                _seenDrop pushBack _id;
                private _vis = ACME_hpmk_visuals getOrDefault [_id,objNull];
                if (isNull _vis) then {
                    private _model = _anchor getVariable ["ACME_hpmk_visualClass", _class];
                    if (_model != "") then {
                        _vis = createSimpleObject [_model, [0,0,0], true];
                        if (!isNull _vis && {_model == "ACME_HPMK_Open"}) then {
                            // Place the hem at the pickup anchor's height. The authored origin is midway through the prop.
                            private _minZ = ((boundingBoxReal _vis) select 0) select 2;
                            _vis setVariable ["ACME_hpmk_groundLift", (-_minZ) max 0];
                        };
                        ACME_hpmk_visuals set [_id, _vis];
                    };
                };
                if (!isNull _vis) then {
                    private _dir = vectorDirVisual _anchor;
                    private _up = vectorUpVisual _anchor;
                    if (vectorDirVisual _vis distance _dir > 0.005 || {vectorUpVisual _vis distance _up > 0.005}) then {_vis setVectorDirAndUp [_dir,_up];};
                    private _position = (getPosWorldVisual _anchor) vectorAdd (_up vectorMultiply (_vis getVariable ["ACME_hpmk_groundLift",0]));
                    if (getPosWorldVisual _vis distance _position > 0.005) then {_vis setPosWorld _position;};
                };
            } forEach ((ACE_player nearObjects ["Land_HelipadEmpty_F", 120]) select {_x getVariable ["ACME_hpmk_isBlanket", false]});
        };
        {
            private _id = _x;
            if !(_id in _seenDrop) then {
                private _vis = ACME_hpmk_visuals get _id;
                if (!isNil "_vis" && {!isNull _vis}) then { deleteVehicle _vis; };
                ACME_hpmk_visuals deleteAt _id;
            };
        } forEach (keys ACME_hpmk_visuals);
    }, 1, []] call CBA_fnc_addPerFrameHandler;
    // A wrapped casualty wears the shell (a vest bound to his bones: ACME_fnc_hpmkDress); nothing is drawn
    // over him here any more.
};
