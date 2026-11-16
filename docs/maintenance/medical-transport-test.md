# Medical transport test

Enable **Addon Options > ACM Extended > SKED > Medical transport diagnostics** in the running mission. Inspect state with **ACE Self Interaction > Audit nearby medical transport**. Search the RPT for **[ACME Transport]**. In multiplayer, collect the server RPT and the RPT of the client who owns the casualty. The server has the authoritative chest viewer count and drawer fraction.

| Test in a mission | Expected evidence |
| --- | --- |
| Strap an unconscious casualty into a SKED. Start, stop and immediately restart solo ACE Drag. Try stopping on uneven ground and while another provider takes over. | The casualty shares the litter's carrier while moving and is attached directly to the litter once settled. The first audit immediately after a transition can show replication in progress. Repeat it after two seconds. |
| Claim two SKED handles, try a third, lift, then release a handle or knock out a bearer. | Two claims are allowed. The default two-person lift sets down once it loses a bearer. Try ACE Drag again after both providers release the handles. |
| Deploy and strap a casualty into a Talon II. Claim two handles, then a third and fourth. Lift and have a follower let go, then have the lead let go. | The lift is offered once three rescuers are attached. It stays up if three remain after a follower releases their handle and sets down when the lead releases. An occupied Talon II has no solo drag. |
| Exercise unstrap, vehicle load/unload and cleanup. Repeat in multiplayer with a player casualty, disconnect a bearer, and observe from a late-joining client. | Lifecycles clear old handles and attachment roots. A stowed litter restores as the same type. Check that the casualty's original ACE drag/carry actions return after unstrapping. |
| Fit HPMK-I and move a casualty from an empty SKED through strap, drag and unstrap. | The occupied audit shows the squeezed vest class when enabled. The normal shell returns after unstrapping. |
| Open a Hardigg chest, view inventory through vanilla and ACE, close the inventory, then close the chest. | The server audit reports the cabinet and lid using the same finish as the closed chest. The drawer fraction settles to 1 while viewed and 0 after everyone leaves. Check lettering, placement and clipping visually. |
| Approach a Hatchet MH-60M or MH-60S with a nearby free seat. | The seat-loading action indicates the Talon II preference. The separate Hatchet placement and hoist implementation can use the interface below. |

For mission scripts, **[providerCount, vehicle] call acme_sked_fnc_preferredLitter** returns the deployed class. The optional vehicle is an Arma object. One or two providers prefer **ACME_SKED_Open**. Three or more providers or a descendant of **vtx_H60_base** prefer **ACME_Talon_Open**. The occupied Talon class is **ACME_Talon_Occupied**. Its Memory LOD contains **handle_hl**, **handle_hr**, **handle_fl**, **handle_fr**, **patient_pos**, **patient_head**, **patient_feet**, **strap_chest**, and **strap_legs**.

The live fold/deploy action swaps the supplied models. The B5 soft skin and animated folding sequence still need an Arma visual test. The separate CPR B6 animation archive was reviewed as source assets and is outside this runtime test.
