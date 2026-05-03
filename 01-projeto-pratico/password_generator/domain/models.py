from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordOptions:
    length: int
    use_uppercase: bool = True
    use_lowercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True
