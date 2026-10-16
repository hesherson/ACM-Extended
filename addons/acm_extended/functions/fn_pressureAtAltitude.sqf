/* Relative ambient pressure, independent of terrain, weather and patient state.
 * Standard-atmosphere lapse layers through 84.852 km; an isothermal tail
 * above the model boundary approaches vacuum. The numerical floor protects
 * gas ratios without the former 11 km / 0.2 physiological plateau.
 */
params [["_height", 0]];
if !(_height isEqualType 0 && {finite _height}) exitWith {1};
_height = (_height max 0) min 1000000;
private _pressure = 1;
private _temperature = 288.15;
private _base = 0;
private _gOverR = 0.034163195;
{
    _x params ["_top", "_lapse"];
    private _end = _height min _top;
    private _distance = (_end - _base) max 0;
    if (_distance > 0) then {
        if (_lapse == 0) then {
            _pressure = _pressure * (exp (-_gOverR * _distance / _temperature));
        } else {
            private _nextTemperature = _temperature + (_lapse * _distance);
            _pressure = _pressure * ((_temperature / _nextTemperature) ^ (_gOverR / _lapse));
            _temperature = _nextTemperature;
        };
    };
    _base = _top;
} forEach [[11000,-0.0065],[20000,0],[32000,0.001],[47000,0.0028],
    [51000,0],[71000,-0.0028],[84852,-0.002]];
if (_height > _base) then {
    _pressure = _pressure * (exp (-_gOverR * (_height - _base) / _temperature));
};
(_pressure max 0.000000001) min 1
