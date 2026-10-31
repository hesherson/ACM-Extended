# 1.2.4.1 / B275 — Connected transfusion menu

- Applies the approved black and grey transfusion design using the existing native body, access and fluid artwork. Occupied-access tags point outward and join their box's top border. Access descriptions are shortened.
- Centers patient identity and shows Blood Type: ??? until the current provider has checked that patient's dog tag.
- Defaults blood preparation to Y tubing, retains direct bag spiking, and labels connected bags [Y] or [PiB]. New Y lines begin flow after priming; Flush Line is offered only for the selected Reserve Flush Saline.
- Adds compatible nonblood piggyback fluids and saline-carrier infusions through Bag Actions and the existing preparation workspace. Add to Piggyback completes the workflow. The secondary drains by gravity before the held primary resumes.
- Shares one downstream Lifewarmer Quantum across connected bags, regardless of which row fits it. Adds saline warming capped at 200 mL/min and plasma warming capped at 100 mL/min, an inline confirmation for the last warmer, and immediate device return on removal. The flowing fluid name and animated Warming... text share orange.
- Preserves attached bags while choosing a move destination and preserves the existing roller-clamp popup and bottom statistics. Removes repeated preparation captions.

Version remains 1.2.4.1 and network protocol remains 1. Native Arma and dedicated-server acceptance remain outstanding. See [the acceptance record](../audits/B275-connected-transfusion-menu.md).
