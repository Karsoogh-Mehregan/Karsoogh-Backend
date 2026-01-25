def validate_national_code(code):
    if not code.isdigit() or len(code) != 10:
        return False

    check = int(code[9])
    s = sum(int(code[i]) * (10 - i) for i in range(9))
    r = s % 11

    return (r < 2 and check == r) or (r >= 2 and check == 11 - r)