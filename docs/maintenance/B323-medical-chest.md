# Medical Chest

In Eden or Zeus, place **Medical Chest (Full Stock)** from **Supplies → ACM**. Its mission classname is `ACME_MedicalChest`. Leave Eden's Simple Object attribute off so it can run its initialization and interactions.

In ACE Interact, **Open Medical Chest** lifts the painted lid clear of the cabinet and swings it to the side. It settles painted-side up as the drawers slide out. Gear opens for the initiating player when the motion finishes, about half a second after the click. Drawer 1 sits at the top, and the open cabinet faces 180° from the closed chest's heading. The server chooses the four- or seven-drawer cabinet and each drawer's extension. With the chest open, ACE shows **Close Medical Chest** on its visible cabinet. To choose between adjacent chests, point at the case you want. Items taken or deposited stay with the same inventory between openings.

Generic chests carry the installed public medical catalog, including ACE, ACM, and ACME medications, airway supplies, fluids, and dressings. They stock four of each major device, eight of most other supplies, and 24 of common dressings and IV consumables. Their Gear container uses a two-million-unit capacity. Hidden compatibility items and runtime-only prepared items are excluded.

## Numbered finishes

B326 adds **Medical Chest 01–10** under the same Eden and Zeus category. The classnames run from `ACME_MedicalChest_01` to `ACME_MedicalChest_10`. B327 replaces finish 02's SURG stencil with handwritten inventory marks. Finishes 03, 06, and 08 have weathered white painter’s tape. Finish 09 has a black cross on its lid. Finish 10 has a blank, scuffed lid and red crosses only on the carry sides. B328 corrects the horizontal projection on the closed and detached lids. B330 adds concentrated abrasion at the molded corner bevels, rub marks on the spacer lips and handle rims, dust in recesses, light scratches across the panels, and deeper drag grooves on the underside. Crates 02, 05, and 07 have rubbed-away stencil remnants. Crate 08 has a lighter shell under the dark olive lid when closed. The OR, PAD, IV FLUIDS, AIRWAY, and BLOOD finishes start with procedure supplies, dressings and splints, IV access and crystalloid supplies, respiratory supplies, and transfusion supplies respectively. The other finishes use generic stock.

Eden shows the upright case and its actual finish while you place and move it. In the crate’s **Attributes**, tick **Start Open** to preview the open cabinet and detached lid and start the mission with the same four-drawer arrangement. Leave the checkbox unticked to start closed. The finish stays with the loose lid after opening and returns to the original chest when it closes. The open shell retains the finish on its exterior panels. The closed case, detached lid, and each open drawer layout use paint and wear geometry fitted to their own stock mesh. This keeps the spray and tape from mirroring across the vanilla UVs. The installed Arma models still provide the shell and drawers.

## Cabinet assets and stencil positioning

The closed stock class is `Land_PortableCabinet_01_closed_olive_F`. The PBO references Bohemia's installed cabinet meshes for the closed case, loose lid and both open variants. The original full-stock chest uses the supplied military stencil lettering for the chipped yellow MEDICAL CHEST and smaller MED-01 markings. Worn black crosses sit between the handles on both sides and in the clear area beside the top handle. The lid and rear panel show old adhesive outlines, with a smaller tape remnant on one carry side. The original transparent decal geometry keeps the lettering readable across shared and mirrored stock UVs. The detached lid shows the front markings on its upward-facing surface. The open cabinet applies case markings where its model exposes a continuous panel.

To see the exact model and texture paths on your install, preview a mission in Eden on VR and execute this in the **local** Debug Console. It prints the model path, camo slots, texture paths, model bounds and drawer animation names to the clipboard.

```sqf
private _classes = [
    "Land_PortableCabinet_01_closed_olive_F",
    "Land_PortableCabinet_01_lid_olive_F",
    "Land_PortableCabinet_01_4drawers_olive_F",
    "Land_PortableCabinet_01_7drawers_olive_F"
];
private _rows = _classes apply {
    private _config = configFile >> "CfgVehicles" >> _x;
    private _probe = _x createVehicleLocal (player getRelPos [8, 0]);
    private _row = [
        _x,
        getText (_config >> "model"),
        getArray (_config >> "hiddenSelections"),
        getObjectTextures _probe,
        boundingBoxReal _probe,
        vectorDir _probe,
        vectorUp _probe,
        animationNames _probe,
        configProperties [_config >> "AnimationSources", "isClass _x", true] apply {configName _x}
    ];
    deleteVehicle _probe;
    _row
};
copyToClipboard ((_rows apply {str _x}) joinString endl);
```

For a texture pass, follow the reported `a3\props_f_enoch\military\camps\…` paths on your Arma Tools project drive. **Project Drive Management → Extract Game Data** populates the drive. BankRev can also unpack just `props_f_enoch.pbo` from your Arma install into a working folder. Open the olive color textures (`*_co.paa`) in TexView 2 and export PNGs. Use the exact paths in the clipboard output since variants can share one texture.

For placement, provide the clipboard output and straight-on screenshots of the upright front, the handle side and the loose lid. For artwork painted directly into the texture, provide an editable UV layout or an authorized texture export as a PNG. A numbered UV-checker screenshot on the lid and handle sides also works for locating the artwork. An editable mesh needs the source **MLOD P3D** or an **FBX/OBJ/Blend with its UVs**. Installed game P3Ds are binarized **ODOL** and serve as game references.

## In-game checks

- Place a chest on ground and one on a raised floor. Check upright orientation and that the lid falls beside the correct face.
- Open and close several times. Check that drawer 1 sits at the top in both layouts, the lid markings face up, and the initiating player enters Gear directly.
- Use two players to open the same chest, take and deposit supplies, and close it with an inventory window open. Verify neither duplicates supplies and both hear one matching clip.
- Join after a chest is open and check that the cabinet, lid, drawer positions and cargo match the other players.
