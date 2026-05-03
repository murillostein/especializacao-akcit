from __future__ import annotations

import math
import secrets
import string

from password_generator.config import Config
from password_generator.domain.models import PasswordOptions


class PasswordGenerationError(ValueError):
    pass


class PasswordService:
    UPPERCASE = string.ascii_uppercase
    LOWERCASE = string.ascii_lowercase
    DIGITS = string.digits
    SYMBOLS = "!@#$%&*()-_=+[]{};:,.?/|"

    @classmethod
    def generate(
        cls,
        length: int | None,
        use_uppercase: bool,
        use_lowercase: bool,
        use_digits: bool,
        use_symbols: bool,
    ) -> str:
        options = cls._normalize_options(
            PasswordOptions(
                length=length if length is not None else Config.DEFAULT_PASSWORD_LENGTH,
                use_uppercase=use_uppercase,
                use_lowercase=use_lowercase,
                use_digits=use_digits,
                use_symbols=use_symbols,
            )
        )
        charset = cls._build_charset(options)
        required_groups = cls._required_groups(options)

        password_chars = [secrets.choice(group) for group in required_groups]
        password_chars.extend(
            secrets.choice(charset) for _ in range(options.length - len(password_chars))
        )
        secrets.SystemRandom().shuffle(password_chars)
        return "".join(password_chars)

    @classmethod
    def evaluate_strength(cls, password: str) -> dict[str, float | int | str]:
        if not password:
            return {"label": "Muito fraca", "score": 0, "entropy": 0.0}

        pool_size = 0
        if any(char in cls.UPPERCASE for char in password):
            pool_size += len(cls.UPPERCASE)
        if any(char in cls.LOWERCASE for char in password):
            pool_size += len(cls.LOWERCASE)
        if any(char in cls.DIGITS for char in password):
            pool_size += len(cls.DIGITS)
        if any(char in cls.SYMBOLS for char in password):
            pool_size += len(cls.SYMBOLS)

        entropy = round(len(password) * math.log2(pool_size), 2) if pool_size else 0.0
        if entropy < 40:
            return {"label": "Muito fraca", "score": 1, "entropy": entropy}
        if entropy < 60:
            return {"label": "Fraca", "score": 2, "entropy": entropy}
        if entropy < 80:
            return {"label": "Boa", "score": 3, "entropy": entropy}
        if entropy < 100:
            return {"label": "Forte", "score": 4, "entropy": entropy}
        return {"label": "Muito forte", "score": 5, "entropy": entropy}

    @classmethod
    def _normalize_options(cls, options: PasswordOptions) -> PasswordOptions:
        if not isinstance(options.length, int):
            raise PasswordGenerationError("O comprimento da senha deve ser um inteiro.")

        if options.length < Config.MIN_PASSWORD_LENGTH:
            raise PasswordGenerationError(
                f"O comprimento minimo e {Config.MIN_PASSWORD_LENGTH} caracteres."
            )
        if options.length > Config.MAX_PASSWORD_LENGTH:
            raise PasswordGenerationError(
                f"O comprimento maximo e {Config.MAX_PASSWORD_LENGTH} caracteres."
            )

        if not any(
            [
                options.use_uppercase,
                options.use_lowercase,
                options.use_digits,
                options.use_symbols,
            ]
        ):
            raise PasswordGenerationError(
                "Selecione ao menos um conjunto de caracteres para gerar a senha."
            )

        return options

    @classmethod
    def _required_groups(cls, options: PasswordOptions) -> list[str]:
        groups = []
        if options.use_uppercase:
            groups.append(cls.UPPERCASE)
        if options.use_lowercase:
            groups.append(cls.LOWERCASE)
        if options.use_digits:
            groups.append(cls.DIGITS)
        if options.use_symbols:
            groups.append(cls.SYMBOLS)
        if options.length < len(groups):
            raise PasswordGenerationError(
                "O comprimento da senha deve comportar todos os grupos selecionados."
            )
        return groups

    @classmethod
    def _build_charset(cls, options: PasswordOptions) -> str:
        charset = ""
        if options.use_uppercase:
            charset += cls.UPPERCASE
        if options.use_lowercase:
            charset += cls.LOWERCASE
        if options.use_digits:
            charset += cls.DIGITS
        if options.use_symbols:
            charset += cls.SYMBOLS
        return charset
