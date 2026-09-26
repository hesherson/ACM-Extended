// an endotracheal tube is a definitive airway. a cuffed tube sitting in the trachea is the whole point of
// intubating someone, because it protects the lower airway from vomit, blood and the tongue. so an intubated
// casualty must be protected from upper-airway obstruction. The i-gel also stents the supraglottic airway,
// but it is not equivalent: ACME's aspiration model gives a cuffed ETT substantially better lower-airway
// protection, and progressive laryngeal/burn edema can defeat or prevent an i-gel while a tube already through
// the cords continues to bypass that upper-airway narrowing.
// ACM gates that protection on ACM_airway_AirwayItem_Oral being "SGA". see handleairwayobstruction_vomit,
// handleairwayobstruction_blood and handleairwaycollapse, which all bail out early when it is set, and ACM's own
// CPR code even comments that check as intubated.
// we deliberately do not simply stamp "SGA" onto an intubated patient, because our EMMA i-gel functions key off
// that same marker, so it would make the game think an i-gel is in place and offer to remove one from a patient
// who has an et tube.
// instead we produce the same net effect the SGA guard produces, where the obstruction never progresses, by holding
// the obstruction and collapse states at zero while the tube is in. ACM's obstruction pfhs keep running
// harmlessly and simply have nothing to act on, which is precisely what their early-exit does for an SGA.
// call it as [_patient] call ACME_fnc_ettAirwayProtect.
params ["_patient"];
if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};
if (!(_patient getVariable ["ACME_ETT_Inserted", false])) exitWith {};
// and the cuff has to be up. an uninflated cuff neither seals the trachea nor keeps anything out of it, so a tube
// sitting there with a flat cuff protects nothing. this is the one thing the tube costs over a supraglottic: the
// prep. Once the cuff is inflated it adds the tube's stronger aspiration seal; the airway-state function also
// preserves the separate advantage of a tracheal tube across severe upper-airway edema.
if (!(_patient getVariable ["ACME_ETT_Inserted", false]) || {!(_patient getVariable ["ACME_ETT_CuffInflated", false])}) exitWith {};
if (!(missionNamespace getVariable ["ACME_ett_protectsAirway", true])) exitWith {};

// vomit and blood cannot reach the lower airway past a cuffed tube.
if ((_patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0]) != 0) then {
    [_patient, [["vomit", 0]], true] call ACM_airway_fnc_setAirwayState;
};
if ((_patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0]) != 0) then {
    [_patient, [["blood", 0]], true] call ACM_airway_fnc_setAirwayState;
};
// the tongue and soft tissue cannot collapse a tracheal tube.
if ((_patient getVariable ["ACM_airway_AirwayCollapse_State", 0]) != 0) then {
    [_patient, [["collapse", 0]], true] call ACM_airway_fnc_setAirwayState;
};

// hold the queue at zero too, not just the current obstruction. ACM's vomit handler is a recurring pfh driven by
// airwayobstructionvomit_count: clearing only the state meant the handler kept coming back and re-obstructing a
// tubed casualty every cycle, and this function kept mopping it up a tick later. with the count held down the
// handler retires itself instead, so the airway is never obstructed in the first place rather than being
// repeatedly repaired. a casualty with a cuffed tube can vomit freely; it simply cannot reach their airway.
if ((_patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0]) != 0) then {
    [_patient, [["vomitCount", 0]], true] call ACM_airway_fnc_setAirwayState;
};
