"""Testes de integração (caminho de sucesso) do gerador de senhas.

Cadeia exercitada: HTTP (Flask test client) -> rota -> PasswordService -> Config.
Nenhuma camada é mockada: as classes reais trabalham juntas.
"""

from __future__ import annotations

import math
import string
from itertools import combinations

import pytest

from password_generator.config import Config

ENDPOINT = "/api/passwords"

# Referência independente dos grupos de caracteres. Repete o contrato do
# PasswordService de propósito: se o serviço mudar, o teste acusa a diferença.
GROUPS: dict[str, str] = {
    "use_uppercase": string.ascii_uppercase,     # 26
    "use_lowercase": string.ascii_lowercase,     # 26
    "use_digits": string.digits,                 # 10
    "use_symbols": "!@#$%&*()-_=+[]{};:,.?/|",   # 24
}
ALL_FLAGS: tuple[str, ...] = tuple(GROUPS)

# PREMISSA A VALIDAR: nomes das chaves do dict devolvido por evaluate_strength.
STRENGTH_ENTROPY_KEY = "entropy"
STRENGTH_LABEL_KEY = "label"
STRENGTH_SCORE_KEY = "score"

ALL_COMBINATIONS: list[tuple[str, ...]] = [
    combo
    for size in range(1, len(ALL_FLAGS) + 1)
    for combo in combinations(ALL_FLAGS, size)
]

REPETICOES_POR_COMBINACAO = 30
CHAMADAS_CONSECUTIVAS = 50


# --------------------------------------------------------------------------- #
# Funções auxiliares
# --------------------------------------------------------------------------- #
def combo_id(selected: tuple[str, ...]) -> str:
    return "+".join(flag.removeprefix("use_") for flag in selected)


def build_payload(selected: tuple[str, ...], **extra) -> dict:
    """Monta o JSON com todas as flags explícitas (True só nas selecionadas)."""
    payload = {flag: flag in selected for flag in ALL_FLAGS}
    payload.update(extra)
    return payload


def post_password(client, **request_kwargs):
    response = client.post(ENDPOINT, **request_kwargs)
    return response, response.get_json(silent=True)


def assert_success_contract(response, body) -> None:
    assert response.status_code == 200
    assert response.is_json
    assert set(body) == {"password", "strength"}
    assert isinstance(body["password"], str)
    assert isinstance(body["strength"], dict)


def allowed_chars(selected: tuple[str, ...]) -> set[str]:
    return set("".join(GROUPS[flag] for flag in selected))


def groups_present(password: str) -> set[str]:
    return {flag for flag, chars in GROUPS.items() if any(c in chars for c in password)}


def expected_strength(password: str) -> tuple[float, str, int]:
    """Recalcula entropia, rótulo e score a partir da senha recebida."""
    pool = sum(len(GROUPS[flag]) for flag in groups_present(password))
    entropy = round(len(password) * math.log2(pool), 2)
    if entropy < 40:
        return entropy, "Muito fraca", 1
    if entropy < 60:
        return entropy, "Fraca", 2
    if entropy < 80:
        return entropy, "Boa", 3
    if entropy < 100:
        return entropy, "Forte", 4
    return entropy, "Muito forte", 5


# --------------------------------------------------------------------------- #
# Testes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "selected",
    [(flag,) for flag in ALL_FLAGS] + [ALL_FLAGS],
    ids=combo_id,
)
def test_gera_senha_por_grupo_de_caracteres(client, selected):
    """INT-F01: cada grupo isolado e todos combinados geram senha válida pela cadeia completa."""
    # Arrange
    payload = build_payload(selected)
    expected_length = Config.DEFAULT_PASSWORD_LENGTH

    # Act
    response, body = post_password(client, json=payload)

    # Assert
    assert_success_contract(response, body)
    password = body["password"]
    assert len(password) == expected_length
    assert set(password) <= allowed_chars(selected)


@pytest.mark.parametrize(
    "request_kwargs",
    [
        pytest.param({"json": {}}, id="length-omitido"),
        pytest.param({"json": {"length": None}}, id="length-null"),
        pytest.param({"json": build_payload(ALL_FLAGS)}, id="flags-explicitas-sem-length"),
        pytest.param({}, id="sem-corpo-json"),
    ],
)
def test_aplica_comprimento_padrao_do_config(client, request_kwargs):
    """INT-F02: sem length (omitido/null/sem corpo), o comprimento padrão vem do Config."""
    # Arrange
    expected_length = Config.DEFAULT_PASSWORD_LENGTH
    assert client.application.config["DEFAULT_PASSWORD_LENGTH"] == expected_length

    # Act
    response, body = post_password(client, **request_kwargs)

    # Assert
    assert_success_contract(response, body)
    assert len(body["password"]) == expected_length
    assert set(body["password"]) <= allowed_chars(ALL_FLAGS)


@pytest.mark.parametrize("limit_name", ["MIN_PASSWORD_LENGTH", "MAX_PASSWORD_LENGTH"])
def test_aceita_limites_exatos_de_comprimento(client, limit_name):
    """INT-F03: os comprimentos mínimo e máximo exatos definidos no Config são aceitos."""
    # Arrange
    length = getattr(Config, limit_name)
    payload = build_payload(ALL_FLAGS, length=length)

    # Act
    response, body = post_password(client, json=payload)

    # Assert
    assert_success_contract(response, body)
    assert len(body["password"]) == length
    assert set(body["password"]) <= allowed_chars(ALL_FLAGS)


@pytest.mark.parametrize(
    ("selected", "length", "expected_label", "expected_score"),
    [
        pytest.param(("use_digits",), 8, "Muito fraca", 1, id="digitos-8"),          # ~26.58
        pytest.param(("use_lowercase",), 10, "Fraca", 2, id="minusculas-10"),       # ~47.00
        pytest.param(("use_uppercase", "use_lowercase"), 12, "Boa", 3,
                     id="letras-12"),                                               # ~68.40
        pytest.param(("use_lowercase", "use_digits"), 16, "Forte", 4,
                     id="minusculas+digitos-16"),                                   # ~82.72
        pytest.param(ALL_FLAGS, 16, "Muito forte", 5, id="todos-16"),               # ~102.82
    ],
)
def test_forca_coerente_com_senha_devolvida(client, selected, length, expected_label, expected_score):
    """INT-F04: strength (entropia, rótulo e score) bate com o recálculo feito a partir da senha recebida."""
    # Arrange
    payload = build_payload(selected, length=length)

    # Act
    response, body = post_password(client, json=payload)

    # Assert
    assert_success_contract(response, body)
    password = body["password"]
    strength = body["strength"]
    entropy, label, score = expected_strength(password)

    assert strength[STRENGTH_ENTROPY_KEY] == pytest.approx(entropy, abs=0.01)
    assert strength[STRENGTH_LABEL_KEY] == label
    assert strength[STRENGTH_SCORE_KEY] == score
    # Confirma que o cenário cai no nível planejado
    assert (label, score) == (expected_label, expected_score)


@pytest.mark.parametrize("selected", ALL_COMBINATIONS, ids=combo_id)
def test_cada_grupo_selecionado_aparece_ao_menos_uma_vez(client, selected):
    """INT-F05: cada grupo selecionado aparece ao menos uma vez e nenhum grupo não selecionado aparece."""
    # Arrange
    payload = build_payload(selected, length=Config.MIN_PASSWORD_LENGTH)

    # Act
    results = [post_password(client, json=payload) for _ in range(REPETICOES_POR_COMBINACAO)]

    # Assert
    for response, body in results:
        assert_success_contract(response, body)
        assert len(body["password"]) == Config.MIN_PASSWORD_LENGTH
        assert groups_present(body["password"]) == set(selected)


def test_chamadas_consecutivas_nao_repetem_senha(client):
    """INT-F06: chamadas consecutivas com o mesmo payload devolvem senhas distintas."""
    # Arrange
    payload = build_payload(ALL_FLAGS)

    # Act
    results = [post_password(client, json=payload) for _ in range(CHAMADAS_CONSECUTIVAS)]

    # Assert
    passwords = []
    for response, body in results:
        assert_success_contract(response, body)
        passwords.append(body["password"])
    assert len(set(passwords)) == CHAMADAS_CONSECUTIVAS


def test_parametros_de_uma_requisicao_nao_vazam_para_a_seguinte(client):
    """INT-F07: a configuração de uma requisição não é reaproveitada pela próxima (sem estado compartilhado)."""
    # Arrange
    restrictive_payload = build_payload(("use_digits",), length=Config.MIN_PASSWORD_LENGTH)

    # Act
    first_response, first_body = post_password(client, json=restrictive_payload)
    second_response, second_body = post_password(client, json={})

    # Assert
    assert_success_contract(first_response, first_body)
    assert len(first_body["password"]) == Config.MIN_PASSWORD_LENGTH
    assert groups_present(first_body["password"]) == {"use_digits"}

    assert_success_contract(second_response, second_body)
    assert len(second_body["password"]) == Config.DEFAULT_PASSWORD_LENGTH
    assert groups_present(second_body["password"]) == set(ALL_FLAGS)


def test_pagina_inicial_e_api_servidas_pela_mesma_aplicacao(client):
    """INT-F08: a página / e a API são servidas pela mesma instância da aplicação."""
    # Arrange
    app = client.application

    # Act
    page = client.get("/")
    api_response, body = post_password(client, json={})

    # Assert
    assert page.status_code == 200
    assert page.mimetype == "text/html"
    assert "Gerador de Senhas" in page.get_data(as_text=True)

    assert_success_contract(api_response, body)
    assert client.application is app
