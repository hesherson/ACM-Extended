# Medical Chest

In Eden or Zeus, place **Medical Chest (Full Stock)** from **Supplies → ACM**. Its mission classname is `ACME_MedicalChest`. Leave Eden's Simple Object attribute off so it can run its initialization and interactions.

The chest starts upright. In ACE Interact, **Open Medical Chest** puts the olive cover on the floor to the side and reveals the four- or seven-drawer cabinet. The server chooses the cabinet and each drawer's extension when opening. Interact with the drawers to **Open Supplies** in Gear or **Close Medical Chest**. The server shares one native inventory between both states, so items taken or deposited remain that way through opening and closing.

The stock is one of each public ACE medical inventory class in the loaded configuration, including ACM and ACME. It includes medical items, charge-bearing medical magazines, and medical backpacks when tagged by a loaded addon. Hidden compatibility classes and runtime-only items that require a prepared-item identity are excluded. Native blood items in this chest follow normal loose-blood rules. Existing ACM Basic and Advanced supply crates remain available.

## Numbered finishes

B326 adds **Medical Chest 01–10** under the same Eden and Zeus category. The classnames run from `ACME_MedicalChest_01` to `ACME_MedicalChest_10`. B327 replaces finish 02's SURG stencil with handwritten inventory marks. Finishes 03, 06, and 08 have weathered white painter’s tape. Finish 09 has a black cross on its lid. Finish 10 has a blank, scuffed lid and red crosses only on the carry sides. B328 corrects the horizontal projection on the closed and detached lids. Scuffs and grooves cluster around the raised ribs, case corners, handle surrounds, and wheel housings. Crates 02, 05, and 07 have rubbed-away stencil remnants. Crate 08 has a lighter shell under the dark olive lid when closed. The markings identify the look of each chest. Each still starts with the full medical inventory.

The finish appears when the mission starts, stays with the loose lid after opening, and returns to the original chest when it closes. The cabinet keeps its handle markings where the open shell has a flat panel. The numbered finishes use paint and wear geometry fitted to the stock panels. This keeps the spray and tape from mirroring across the vanilla UVs. The installed Arma models still provide the shell and drawers.

## Cabinet assets and stencil positioning

The closed stock class is `Land_PortableCabinet_01_closed_olive_F`. The PBO references Bohemia's installed cabinet meshes for the closed case, loose lid and both open variants. The original full-stock chest uses the supplied military stencil lettering for the chipped yellow MEDICAL CHEST and smaller MED-01 markings. Worn black crosses sit between the handles on both sides and in the clear area beside the top handle. The lid and rear panel show old adhesive outlines, with a smaller tape remnant on one carry side. The original transparent decal geometry keeps the lettering readable across shared and mirrored stock UVs. The detached lid retains the front markings and rests painted side up. The open cabinet applies case markings where its model exposes a continuous panel.

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
- Open and close several times. Check both drawer layouts and the orientation of the stencil on the detached lid.
- Use two players to open the same chest, take and deposit supplies, and close it with an inventory window open. Verify neither duplicates supplies and both hear one matching clip.
- Join after a chest is open and check that the cabinet, lid, drawer positions and cargo match the other players.
