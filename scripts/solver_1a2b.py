# 1A2B Solver Logic
import itertools

def get_ab(guess, target):
    a, b = 0, 0
    for i in range(len(guess)):
        if guess[i] == target[i]: a += 1
        elif guess[i] in target: b += 1
    return a, b

def solve_next(history):
    """
    history: list of [guess_str, a, b]
    """
    possible_numbers = ["".join(p) for p in itertools.permutations("0123456789", 4)]
    filtered = []
    for num in possible_numbers:
        match = True
        for prev_guess, a, b in history:
            if a is None or b is None: continue
            pa, pb = get_ab(prev_guess, num)
            if pa != a or pb != b:
                match = False
                break
        if match: filtered.append(num)
    if not filtered: return None
    return filtered[0], len(filtered)
