/* Exact physical battery classes, fresh first then highest remaining charge. */
private _items = missionNamespace getVariable ["ACME_vent_batteryItemClasses", []];
if (_items isEqualTo []) then {
    _items = ["ACME_VentBattery"];
    for "_charge" from 99 to 0 step -1 do {_items pushBack format ["ACME_VentBattery_%1", _charge];};
    missionNamespace setVariable ["ACME_vent_batteryItemClasses", _items];
};
+_items
