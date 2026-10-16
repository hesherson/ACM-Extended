// discard the y tubing on the currently selected access. this is the only action that tears a y line down, because
// pulling individual bags always leaves empty markers and keeps the structure, in fn_transfusionpullbag.
// discarding does the following.
// it pushes every bag on the access that still holds fluid into the used-bag store with its exact remaining volume,
// the same as pull bag, so nothing is wasted.
// it removes all bag entries for the access, both live bags and empty markers.
// it removes the key of the access from ACME_YLines, freeing the site for any other iv setup.
// it drops any medicated-infusion records still tied to the access.
// it does not refund a y-tubing set, because the tubing is consumed: it was cut off the line.
// it is wired to the repurposed 86120 button, "Discard Y Tubing", and is enabled only when the selected access
// carries a y.
// call it as [] call ACME_fnc_discardYTubing.
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _target=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _part=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
private _iv=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
private _site=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
if (isNull _target || {_part==""} || {_site<0}) exitWith {};
if !([_target,_part,_iv,_site] call ACME_fnc_isYLineAccess) exitWith {["No Y tubing on this access.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};
private _requestId=format ["ydiscard:%1:%2:%3",clientOwner,diag_frameNo,floor(diag_tickTime*1000)];
private _pending=uiNamespace getVariable ["ACME_yDiscardPending",createHashMap];
_pending set [_requestId,[ACE_player,_target]];
uiNamespace setVariable ["ACME_yDiscardPending",_pending];
private _identity=[];
{if ((_x param [3,-1]) == _site && {(_x param [4,true]) isEqualTo _iv}) then {_identity pushBack (_x param [8,""]);};}
    forEach ((_target getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]]);
_identity sort true;
[_target,"discardYTubing",[_target,ACE_player,_part,_iv,_site,[_target] call ACME_fnc_clinicalEpoch,_requestId,serverTime,_identity]] call ACME_fnc_ownerDispatch;
