/* Reference adult half-lives in seconds: [terminal, clinical, initial, initial fraction].
 * An omitted clinical value uses terminal washout. Zero retains the native effect curve.
 * Initial fractions are concentration-model estimates for multiphasic drugs. */
createHashMapFromArray [
    ["adenosine", [5,5]],
    ["epinephrine", [180]],
    ["epinephrinecardiac", [180]],
    ["norepinephrine", [144]],
    ["esmolol", [540]],
    ["atropine", [10800]],
    ["lidocaine", [6000,6000,480,0.70]],
    ["amiodarone", [1728000,0,600,0.99]],
    ["morphine", [7200]],
    ["fentanyl", [13140,900,780,0.85]],
    ["ketamine", [9000,750,750,0.80]],
    ["esketamine", [32400,0,0,0]],
    ["midazolam", [10800,1800]],
    ["propofol", [19800,0,2400,0.95]],
    ["rocuronium", [4380,0]],
    ["sugammadex", [7200,0]],
    ["naloxone", [7200]],
    ["ondansetron", [12600]],
    ["txa", [7200]],
    ["ceftriaxone", [25200]],
    ["ertapenem", [14400]],
    ["moxifloxacin", [43200]],
    ["paracetamol", [9000]],
    ["penthrox", [11376,0]],
    ["phentolamine", [1140,0]],
    ["magnesium", [16200]]
]
