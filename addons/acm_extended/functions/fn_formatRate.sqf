params ["_doseRemaining", "_remainingVolume", "_dropSet", "_dropsPerMinute", ["_clampPosition", -1]];

private _mlPerMinute = if (_dropSet > 0) then {_dropsPerMinute / _dropSet} else {0};
private _minutesLeft = if (_mlPerMinute > 0) then {(_remainingVolume max 0) / _mlPerMinute} else {0};
private _rateText = if (_dropsPerMinute < 10) then {_dropsPerMinute toFixed 1} else {str (round _dropsPerMinute)};
private _timeText = if (_mlPerMinute <= 0) then {"stopped"} else {if (_minutesLeft >= 60) then {format ["~%1 hr", (_minutesLeft / 60) toFixed 1]} else {format ["~%1 min", round _minutesLeft]}};
private _mlText = if (_mlPerMinute < 10) then {_mlPerMinute toFixed 1} else {str (round _mlPerMinute)};
private _clampText = "";

// A gravity set exposes drops and fluid flow, not an exact delivered medication rate.
private _mgText = "";

if (_clampPosition >= 0) then {
    _clampText = format [" | %1%2 open", round (((_clampPosition max 0) min 1) * 100), "%"];
};

format ["%1 gtt/mL | %2 gtt/min | %3 mL/min%6 | %4%5", round _dropSet, _rateText, _mlText, _timeText, _clampText, _mgText]
