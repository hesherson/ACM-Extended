/* Resolve the physical drawable medication item classname for a medication key.
   Extended-owned cardiac epinephrine uses the ACME_ namespace. Native ACM Dimercaprol is an ampule but still
   participates in ACM's vial/syringe system, so it must retain its native ACM_Ampule_ classname.
*/
params [["_med", "", [""]]];
if (_med == "") exitWith {""};
if (_med == "EpinephrineCardiac") exitWith {"ACME_Vial_EpinephrineCardiac"};
if (_med == "Dimercaprol") exitWith {"ACME_Ampule_Dimercaprol"};
format ["ACME_Vial_%1", _med]
