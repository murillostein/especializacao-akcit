import string

import pytest

from password_generator.services.password_service import (
    PasswordGenerationError,
    PasswordService,
)


def test_generate_password_respects_length():
    password = PasswordService.generate(24, True, True, True, True)
    assert len(password) == 24


def test_generate_password_includes_selected_groups():
    password = PasswordService.generate(16, True, True, True, True)
    assert any(char in string.ascii_uppercase for char in password)
    assert any(char in string.ascii_lowercase for char in password)
    assert any(char in string.digits for char in password)
    assert any(char in PasswordService.SYMBOLS for char in password)


def test_generate_password_with_single_group():
    password = PasswordService.generate(12, False, False, True, False)
    assert set(password).issubset(set(string.digits))


def test_generate_password_requires_one_group():
    with pytest.raises(PasswordGenerationError):
        PasswordService.generate(12, False, False, False, False)


def test_generate_password_validates_minimum_length():
    with pytest.raises(PasswordGenerationError):
        PasswordService.generate(4, True, False, False, False)


def test_generate_password_validates_required_group_count():
    with pytest.raises(PasswordGenerationError):
        PasswordService.generate(3, True, True, True, True)


def test_evaluate_strength_for_empty_password():
    result = PasswordService.evaluate_strength("")
    assert result["score"] == 0
    assert result["entropy"] == 0.0


def test_evaluate_strength_for_strong_password():
    result = PasswordService.evaluate_strength("Ab9!Ab9!Ab9!Ab9!")
    assert result["score"] >= 4
    assert result["entropy"] > 80
