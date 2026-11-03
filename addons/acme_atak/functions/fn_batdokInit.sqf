if (isNil "ACME_batdok_roster") then { ACME_batdok_roster = [] };
["ace_treatmentSucceded", { _this call ACME_fnc_batdokTreat }] call CBA_fnc_addEventHandler;
if (isServer && {isNil "ACME_batdok_tick"}) then { ACME_batdok_tick = [ACME_fnc_batdokTick, 5] call CBA_fnc_addPerFrameHandler };
