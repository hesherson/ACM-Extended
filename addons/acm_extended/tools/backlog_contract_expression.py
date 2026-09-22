"""Fail-closed extraction of one shipped SQF assignment for arithmetic probes.

This does not compile SQF or establish clinical correctness. It only identifies
an unambiguous expression while ignoring commented and quoted examples.
"""
from source_scan import lex

def assignment_expression(text, name):
    """Extract one actual private assignment, including multiline/nested expressions.

    Comments and quoted examples cannot become candidates. Missing, duplicated or
    unterminated assignments fail closed instead of silently selecting old text.
    """
    from source_scan import matching
    tokens = lex(text)
    pairs = matching(tokens)
    candidates = []
    for i in range(len(tokens) - 3):
        if not (tokens[i].kind == 'ident' and tokens[i].value == 'private'
                and tokens[i+1].kind == 'ident' and tokens[i+1].value == name
                and tokens[i+2].value == '='):
            continue
        j = i + 3
        while j < len(tokens):
            t = tokens[j]
            if t.kind == 'symbol' and t.value in ('[', '(', '{'):
                if j not in pairs:
                    raise AssertionError(f'Unbalanced assignment: {name}')
                j = pairs[j] + 1
                continue
            if t.kind == 'symbol' and t.value == ';':
                candidates.append(text[tokens[i+3].offset:t.offset].strip())
                break
            j += 1
        else:
            raise AssertionError(f'Unterminated assignment: {name}')
    if len(candidates) != 1:
        raise AssertionError(f'Expected one private assignment for {name}; found {len(candidates)}')
    return candidates[0]
