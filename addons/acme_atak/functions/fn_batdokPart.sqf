params [["_p", ""]];
switch (toLowerANSI _p) do {
	case "head": {"Head"};
	case "body": {"Torso"};
	case "leftarm": {"Left arm"};
	case "rightarm": {"Right arm"};
	case "leftleg": {"Left leg"};
	case "rightleg": {"Right leg"};
	default {""};
}
