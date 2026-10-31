# 1.2.4.1 / B277 — Ventilator oxygen and transfusion styling

- Requires a usable oxygen cylinder for ventilator FiO2 enrichment while preserving battery-powered room-air ventilation. Oxygen availability gates only FiO2; other settings keep their existing behavior and restrictions.
- Shows oxygen source/reserve on the existing O2 page and consumes finite cylinder gas only for actual enriched breaths. Supply loss or depletion returns effective FiO2 to room air without stopping battery-powered ventilation.
- Exposes manual FiO2 in Simple ventilation while preserving automatic pressure and ventilation settings.
- Prevents accepted manual breaths from replaying after receipt-history eviction or patient locality changes, preserving once-only delivered volume and oxygen debits.
- Applies native rounded black and grey transfusion cards and cleaner spacing closer to the approved preview, using existing ACM body, access and fluid artwork. Narrow cards keep full piggyback roles and warming text readable; native button focus and stock/prepared scrolling remain available.
- Binds each card to physical bag or prepared-set custody, hides stale access metadata, and keeps the Prepared IV Sets toggle transparent through repeated refreshes.
- Preserves prepared sets and infusions, Y tubing, piggyback priority, downstream warmers, priming and flush controls, pending bag-move custody and the existing roller-clamp popup.

Version remains 1.2.4.1 and network protocol remains 1. Native Arma and dedicated-server acceptance remain outstanding. See [the acceptance record](../audits/B277-ventilator-oxygen-and-transfusion-style.md).
