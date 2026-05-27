import random
import string


CHARACTERS = string.ascii_letters + string.digits  # a-z, A-Z, 0-9


def generate_short_code(length: int = 6) -> str:
    return "".join(random.choices(CHARACTERS, k=length))