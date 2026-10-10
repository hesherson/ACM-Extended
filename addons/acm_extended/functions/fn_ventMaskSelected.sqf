/* B223: explicit NIV+CPAP selections override Simple delivery, even before mask replication.
   Read-only: presetting a carried ventilator never attaches equipment to its owner. */
params [["_patient", objNull, [objNull]]];
!isNull _patient && {(_patient getVariable ["ACME_vent_mode", ""]) == "CPAP PS HF"}
    && {(_patient getVariable ["ACME_vent_iface", ""]) in ["NON INVASIVE", "NON-INVASIVE"]}
