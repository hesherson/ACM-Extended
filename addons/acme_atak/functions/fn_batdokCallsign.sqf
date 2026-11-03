params [["_u", objNull]];
if (isNull _u) exitWith {""};
private _g = group _u;
if (isNull _g) exitWith { name _u };
format ["%1_%2", ((groupId _g) splitString " ") joinString "", ((units _g) find _u) + 1]
