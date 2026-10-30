params ["_date"];
if !(_date isEqualType [] && {count _date >= 3}) exitWith {""};
_date params ["_year", "_month", "_day"];
if !(_year isEqualType 0 && {_month isEqualType 0} && {_day isEqualType 0}
    && {_month >= 1} && {_month <= 12}) exitWith {""};
private _months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
format ["%1-%2-%3", _day, _months select (floor _month - 1), ((str _year) select [2, 2])]
