/* Concise attachment feedback; diagnostic internals stay in the RPT. */
params [["_reason", "", [""]]];
switch (_reason) do {
    case "line-occupied": {"There is already a bag on this line."};
    case "access-missing": {"Select an available IV/IO access first."};
    case "blood-y-line": {"Medication infusions cannot use a blood Y-line."};
    case "patient-unavailable": {"No patient selected."};
    case "provider-unavailable": {"Provider unavailable."};
    case "out-of-range": {"Move closer to the patient."};
    case "patient-changed": {"Patient changed. Select the access again."};
    case "prepared-set-missing": {"That prepared set is no longer available."};
    case "carrier-identity": {"Could not identify the new carrier bag."};
    case "medication-registration": {"Could not register the infusion medication."};
    case "set-already-attached": {"This prepared set is already attached."};
    case "request-mismatch": {"Attachment request changed. Try again."};
    default {"The selected access or prepared set changed."};
}
