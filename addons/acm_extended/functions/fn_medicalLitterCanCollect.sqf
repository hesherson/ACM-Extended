/* Any controlled, conscious on-foot player can collect anybody's registered litter. No medical-role gate. */
params [["_unit",objNull,[objNull]],["_continuing",false,[false]]];
if (isNull _unit || {!local _unit} || {!alive _unit} || {_unit isNotEqualTo (call ACME_fnc_controlledProvider)}
    || {_unit getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _unit}
    || {stance _unit == "PRONE"}) exitWith {false};
if (!_continuing && {(_unit getVariable ["ACME_litterCollect",[]]) isNotEqualTo []}) exitWith {false};
if ([_unit,false,true] call ACME_fnc_providerStanceOwned) exitWith {false};
true
