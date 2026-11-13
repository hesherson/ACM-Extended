params ["_actor","_device"];
if (isNull _actor || {!alive _actor} || {!(_actor isKindOf "CAManBase")}
    || {isNull _device} || {!alive _device} || {_actor distance _device > 3.5}
    || {_actor getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _actor}
    || {_actor getVariable ["ACME_persistenceFrozen",false]}
    || {!isNull attachedTo _device} || {isObjectHidden _device}) exitWith {false};
if ((_device getVariable ["ACME_eq_busy",false]) || {_device getVariable ["ACME_eq_restoreStaged",false]}
    || {_device getVariable ["ace_dragging_isDragged",false]} || {_device getVariable ["ace_dragging_isCarried",false]}
    || {_device getVariable ["ACME_coolerRetired",false]} || {_device getVariable ["ACME_coolerPacking",false]}) exitWith {false};
private _patient = _device getVariable ["ACME_eq_patient",objNull];
if (_patient getVariable ["ACME_persistenceFrozen",false]) exitWith {false};
(_device isKindOf "ACME_TempusPro") || {_device isKindOf "ACME_TempusLS"}
    || {_device isKindOf "ACME_AccuvacRescue"} || {_device isKindOf "ACME_VentwaySparrow_Bare"}
    || {_device isKindOf "ACME_TempusPro_Mount" && {isNull (_device getVariable ["ACME_eq_device",objNull])}}
    || {_device isKindOf "ACME_HPMK_Pouch"}
    || {_device isKindOf "Land_HelipadEmpty_F" && {_device getVariable ["ACME_hpmk_dropped",false]}}
    || {(typeOf _device) in ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"]}
