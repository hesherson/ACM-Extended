#include "script_component.hpp"
if (missionNamespace getVariable ["DD1380_card_eventsRegistered", false]) exitWith {};
missionNamespace setVariable ["DD1380_card_eventsRegistered", true];
["LNX_DD1380_Open", {_this call DD1380_card_fnc_openCardLocal}] call CBA_fnc_addEventHandler;
["LNX_DD1380_Flip", {_this call DD1380_card_fnc_flipPageLocal}] call CBA_fnc_addEventHandler;
["LNX_DD1380_DocumentRequest", {_this call DD1380_card_fnc_requestDocument}] call CBA_fnc_addEventHandler;
["LNX_DD1380_OpenReady", {_this call DD1380_card_fnc_openReady}] call CBA_fnc_addEventHandler;
["LNX_DD1380_Save", {_this call DD1380_card_fnc_receiveData}] call CBA_fnc_addEventHandler;
["LNX_DD1380_SaveAck", {_this call DD1380_card_fnc_saveAck}] call CBA_fnc_addEventHandler;
