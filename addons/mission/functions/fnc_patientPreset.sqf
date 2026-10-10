#include "..\script_component.hpp"
/* B216: reusable clinical cases for the existing training computer.
 * [id, title, triage, wounds, fractures, blood, airway, chest, TBI, blast, CBRN]
 * Triage labels describe the initial exercise, not a permanent triage override.
 * An empty id returns the catalog. Random parents still use generatePatient.
 */
params [["_id", "", [""]]];
private _none = [false,false,false,false];
private _normalBlood = [6,0,0,3];
private _presets = [
    ["abrasions", "Minor abrasions", 1, [["Abrasion",0,2,false,"leftleg"]], _none, _normalBlood, [0,0], [], [], 0, []],
    ["laceration", "Minor arm laceration", 1, [["Laceration",0,1,false,"leftarm"]], _none, _normalBlood, [0,0], [], [], 0, []],
    ["fracture", "Isolated leg fracture", 2, [["Contusion",1,1,false,"rightleg"]], [false,false,false,true], _normalBlood, [0,0], [], [], 0, []],
    ["tbi_moderate", "Moderate TBI", 2, [["Contusion",1,1,false,"head"]], _none, _normalBlood, [0,0], [], [0.45,1], 0, []],
    ["simple_ptx", "Simple pneumothorax", 2, [["VelocityWound",0,1,false,"body"]], _none, [5.5,0,0,3], [0,0], [1,0], [], 0, []],
    ["blast_mild", "Mild blast lung", 2, [], _none, _normalBlood, [0,0], [], [], 0.25, []],
    ["tension_ptx", "Tension pneumothorax", 3, [["VelocityWound",1,1,false,"body"]], _none, [5,0,0,3], [0,0], [2,0], [], 0, []],
    ["hemothorax", "Hemothorax", 3, [["VelocityWound",1,1,false,"body"]], _none, [4.5,0,0,3], [0,0], [3,0,6,1], [], 0, []],
    ["tbi_severe", "Severe TBI", 3, [["Contusion",2,1,false,"head"]], _none, _normalBlood, [0,0], [], [0.8,2], 0, []],
    ["blast_severe", "Severe blast lung", 3, [], _none, _normalBlood, [0,0], [], [], 0.7, []],
    ["hemorrhage", "Major limb hemorrhage", 3, [["Avulsion",2,2,true,"leftleg"]], _none, [3.5,0,0,2], [0,0], [], [], 0, []],
    ["airway", "Obstructed airway / secretions", 3, [], _none, _normalBlood, [0.8,0.6], [], [], 0, []],
    ["tbi_herniation", "Herniating TBI", 4, [["Contusion",2,1,false,"head"]], _none, _normalBlood, [0,0.5], [], [0.95,3], 0, []],
    ["polytrauma", "Critical blast polytrauma", 4, [["Avulsion",2,1,true,"rightleg"],["VelocityWound",1,1,false,"body"]], [false,false,false,true], [3,0,0,1.5], [0.3,0.4], [3,1,7,1.5], [0.65,2], 0.7, []],
    ["massive_htx", "Massive hemothorax / shock", 4, [["VelocityWound",2,1,false,"body"]], _none, [3,0,0,2], [0,0], [3,1,9,1.5], [], 0, []],
    ["cbrn_cs", "CS exposure (Routine)", 1, [], _none, _normalBlood, [0,0], [], [], 0, ["Chemical_CS",30]],
    ["cbrn_chlorine", "Chlorine inhalation (Priority)", 2, [], _none, _normalBlood, [0,0], [], [], 0, ["Chemical_Chlorine",25]],
    ["cbrn_sarin", "Sarin poisoning (Immediate)", 3, [], _none, _normalBlood, [0,0], [], [], 0, ["Chemical_Sarin",40]],
    ["cbrn_sarin_severe", "Severe sarin poisoning (Expectant)", 4, [], _none, _normalBlood, [0,0], [], [], 0, ["Chemical_Sarin",80]]
];
if (_id == "") exitWith {_presets};
private _index = _presets findIf {(_x select 0) == _id};
if (_index < 0) exitWith {[]};
_presets select _index
