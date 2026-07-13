BASE = "0123456789ABCDEFGHJKLMNPQRTUWXY"
WEIGHTS = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]


def is_valid_uscc(value: str) -> bool:
    code = value.strip().upper()
    if len(code) != 18:
        return False
    if any(char not in BASE for char in code):
        return False
    total = sum(BASE.index(char) * weight for char, weight in zip(code[:17], WEIGHTS))
    check_index = 31 - total % 31
    if check_index == 31:
        check_index = 0
    return BASE[check_index] == code[-1]

