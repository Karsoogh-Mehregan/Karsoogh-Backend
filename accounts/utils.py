def validate_national_code(code):
    if not code.isdigit() or len(code) != 10:
        return False

    check = int(code[9])
    s = sum(int(code[i]) * (10 - i) for i in range(9))
    r = s % 11

    return (r < 2 and check == r) or (r >= 2 and check == 11 - r)


def normalize_phone(phone):
    if phone is None:
        return ""
    return str(phone).strip()


def validate_phone(phone):
    phone = normalize_phone(phone)
    return phone.isdigit() and len(phone) == 11 and phone.startswith("09")
