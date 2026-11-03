params ["_class"];
if ((_class find "ACME_SpoiledBlood")==0) exitWith {_class};
private _volume=[_class] call ACME_fnc_coolerBagVolume;
format ["ACME_SpoiledBlood_%1",[500,_volume] select (_volume in [250,500,1000])]
