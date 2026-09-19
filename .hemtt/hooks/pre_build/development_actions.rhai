// Branch names are not a release boundary. Build and release outputs must omit development actions.
// Work on HEMTT's virtual files so a release never changes the checked-out dev source.
let development = HEMTT.is_dev() || HEMTT.is_launch();
let begin_marker = "// ACME_DEV_ONLY_BEGIN";
let end_marker = "// ACME_DEV_ONLY_END";
let files = [
    "addons/acm_extended/config.cpp",
    "addons/gui/overrides/fnc_updateActions.sqf",
    "addons/acm_extended/functions/fn_postInit.sqf"
];
for name in files {
    let path = HEMTT_VFS.join(name);
    let source = path.open_file().read();
    if name == "addons/acm_extended/config.cpp" {
        if !source.contains("acme_developmentBuild = 0;") {
            fatal("Missing default-off development build marker in " + name);
        }
        if development {
            source.replace("acme_developmentBuild = 0;", "acme_developmentBuild = 1;");
        }
    }
    if !development {
        while source.contains(begin_marker) {
            let first = source.index_of(begin_marker);
            let last = source.index_of(end_marker);
            if last < first {
                fatal("Unpaired development action block in " + name);
            }
            source = source.sub_string(0, first) + source.sub_string(last + end_marker.len());
        }
        if source.contains(end_marker) {
            fatal("Unpaired development action end marker in " + name);
        }
        // Fail the build if an action or its installer escaped the marked blocks.
        for forbidden in [
            "ACME_AttachDragHandle", "ACME_ReleaseDragHandle",
            "ACME_DragHandleAttach", "ACME_DragHandleRelease",
            "Attach Drag Handle", "Release Drag Handle",
            "call ACME_fnc_initDragHandleRuntime"
        ] {
            if source.contains(forbidden) {
                fatal("Development drag handle entry escaped release filtering: " + name);
            }
        }
    }
    path.create_file().write(source);
}
if !development {
    print("ACME release guard: experimental drag handle actions excluded");
}
