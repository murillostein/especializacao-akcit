"""Testes de contrato orientados ao consumidor (CDC) para POST /api/passwords.

Consumidor: static/js/app.js (frontend)
Provedor:   routes.py + PasswordService (Flask)

O contrato não está documentado: ele foi inferido do código dos dois lados.
Os schemas abaixo (JSON Schema draft 2020-12, subconjunto) são a fonte de
verdade deste arquivo. A fixture `client` vem de conftest.py.
"""

import itertools
import json
import math
import string

import pytest

ENDPOINT = "/api/passwords"

# ---------------------------------------------------------------------------
# Schemas do contrato
# ---------------------------------------------------------------------------
STRENGTH_LABELS = ["Muito fraca", "Fraca", "Boa", "Forte", "Muito forte"]

REQUEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:contrato:api-passwords:request",
    "title": "POST /api/passwords - requisicao",
    "type": "object",
    "required": ["length", "use_uppercase", "use_lowercase", "use_digits", "use_symbols"],
    "properties": {
        "length": {
            "type": "integer",
            "minimum": 8,
            "maximum": 64,
            "description": "Number(valor do <input type=range min=8 max=64>)",
        },
        "use_uppercase": {"type": "boolean"},
        "use_lowercase": {"type": "boolean"},
        "use_digits": {"type": "boolean"},
        "use_symbols": {"type": "boolean"},
    },
    "additionalProperties": False,
}

RESPONSE_200_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:contrato:api-passwords:response-200",
    "title": "POST /api/passwords - resposta 200",
    "type": "object",
    "required": ["password", "strength"],
    "properties": {
        "password": {"type": "string"},
        "strength": {
            "type": "object",
            "required": ["label", "entropy"],
            "properties": {
                "label": {"type": "string", "enum": STRENGTH_LABELS},
                "entropy": {"type": "number", "minimum": 0},
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Retornado pelo provedor, nao lido pelo consumidor",
                },
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

RESPONSE_400_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:contrato:api-passwords:response-400",
    "title": "POST /api/passwords - resposta 400",
    "type": "object",
    "required": ["error"],
    "properties": {"error": {"type": "string"}},
    "additionalProperties": True,
}

# ---------------------------------------------------------------------------
# Validador mínimo (apenas o necessário para os schemas acima)
# ---------------------------------------------------------------------------
SUPPORTED_KEYWORDS = frozenset(
    {
        "$schema", "$id", "title", "description",  # anotações (ignoradas)
        "type", "required", "properties", "enum",
        "minimum", "maximum", "additionalProperties",
    }
)


def _is_number(value):
    # bool é subclasse de int em Python, mas em JSON/JS não é número.
    # NaN/Infinity não existem em JSON válido.
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_integer(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value) and value.is_integer()


TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": _is_integer,
    "number": _is_number,
    "null": lambda v: v is None,
}


def validate(instance, schema, path="$"):
    """Retorna a lista de violações (vazia = válido)."""
    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        # Evita a falsa sensação de segurança de uma palavra-chave ignorada.
        raise ValueError(f"{path}: palavras-chave nao suportadas: {sorted(unknown)}")

    expected = schema.get("type")
    if expected is not None and not TYPE_CHECKS[expected](instance):
        return [f"{path}: esperado '{expected}', recebido {type(instance).__name__} ({instance!r})"]

    errors = []

    if "enum" in schema and not any(
        type(instance) is type(option) and instance == option for option in schema["enum"]
    ):
        errors.append(f"{path}: {instance!r} fora do enum {schema['enum']!r}")

    if _is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance!r} < minimum {schema['minimum']!r}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance!r} > maximum {schema['maximum']!r}")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: campo obrigatorio ausente '{name}'")
        additional_allowed = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in properties:
                errors.extend(validate(value, properties[name], f"{path}.{name}"))
            elif additional_allowed is False:
                errors.append(f"{path}: campo nao previsto '{name}'")

    return errors


def assert_valid(instance, schema):
    errors = validate(instance, schema)
    assert not errors, f"Violacao do contrato '{schema['title']}':\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Simulação fiel do consumidor (app.js)
# ---------------------------------------------------------------------------
CHECKBOXES = ("use_uppercase", "use_lowercase", "use_digits", "use_symbols")
SLIDER_MIN, SLIDER_MAX = 8, 64  # atributos min/max do <input type="range">
LENGTH_SAMPLE = (8, 9, 16, 33, 63, 64)  # limites, vizinhos dos limites, padrão e meio
assert all(SLIDER_MIN <= n <= SLIDER_MAX for n in LENGTH_SAMPLE)


def simulate_form_data(length, checked):
    """Replica o FormData do navegador.

    - o slider envia o valor como string;
    - um checkbox marcado envia "on";
    - um checkbox desmarcado NÃO aparece (formData.get -> null).
    """
    form = {"length": str(length)}
    form.update({name: "on" for name in checked})
    return form


def build_consumer_payload(form):
    """Tradução literal do bloco `payload` de app.js."""
    return {
        "length": int(form.get("length")),  # Number("16") -> 16; o slider só gera inteiros
        "use_uppercase": form.get("use_uppercase") == "on",
        "use_lowercase": form.get("use_lowercase") == "on",
        "use_digits": form.get("use_digits") == "on",
        "use_symbols": form.get("use_symbols") == "on",
    }


_ABBR = {"use_uppercase": "U", "use_lowercase": "L", "use_digits": "D", "use_symbols": "S"}

FLAG_COMBOS = [
    frozenset(name for name, on in zip(CHECKBOXES, bits) if on)
    for bits in itertools.product((True, False), repeat=len(CHECKBOXES))
]


def _case(length, checked):
    payload = build_consumer_payload(simulate_form_data(length, checked))
    flags = "".join(_ABBR[n] for n in CHECKBOXES if n in checked) or "nenhum"
    return pytest.param(payload, id=f"len{length}-{flags}")


# 15 combinações com pelo menos um checkbox x 6 comprimentos
SUCCESS_CASES = [_case(n, c) for n in LENGTH_SAMPLE for c in FLAG_COMBOS if c]
# todos os checkboxes desmarcados
ERROR_CASES = [_case(n, frozenset()) for n in LENGTH_SAMPLE]
ALL_CASES = SUCCESS_CASES + ERROR_CASES


def send_like_consumer(client, payload):
    """Equivalente ao fetch() de app.js: POST, JSON.stringify, Content-Type JSON."""
    return client.post(
        ENDPOINT,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )


def _reject_non_standard_constant(token):
    raise ValueError(f"constante JSON invalida para o navegador: {token}")


def read_json_like_browser(response):
    """Equivalente a response.json(): JSON.parse estrito (rejeita NaN/Infinity)."""
    body = response.get_data(as_text=True)
    try:
        return json.loads(body, parse_constant=_reject_non_standard_constant)
    except ValueError as exc:
        pytest.fail(f"response.json() falharia no navegador: {exc}\nCorpo: {body[:300]!r}")


def assert_json_content_type(response):
    content_type = response.headers.get("Content-Type", "")
    media_type = content_type.split(";")[0].strip().lower()
    assert media_type == "application/json", (
        f"Content-Type esperado 'application/json', recebido {content_type!r} "
        f"(status {response.status_code})"
    )


_ALL_ON = {name: True for name in CHECKBOXES}

# ---------------------------------------------------------------------------
# Testes: sanidade das entradas e do validador
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload", ALL_CASES)
def test_payloads_do_consumidor_respeitam_schema_de_requisicao(payload):
    """INT-C01 — Todo payload que a simulação do consumidor produz (slider 8–64,
    checkboxes booleanos, inclusive todos desmarcados) é válido no schema de
    requisição. Isso garante que os testes do provedor usem só entradas reais."""
    assert_valid(payload, REQUEST_SCHEMA)


@pytest.mark.parametrize(
    "instance, schema",
    [
        pytest.param({**_ALL_ON, "length": "16"}, REQUEST_SCHEMA, id="req-length-string"),
        pytest.param({**_ALL_ON, "length": 16.5}, REQUEST_SCHEMA, id="req-length-fracionario"),
        pytest.param({**_ALL_ON, "length": True}, REQUEST_SCHEMA, id="req-length-bool"),
        pytest.param({**_ALL_ON, "length": 7}, REQUEST_SCHEMA, id="req-length-abaixo-min"),
        pytest.param({**_ALL_ON, "length": 65}, REQUEST_SCHEMA, id="req-length-acima-max"),
        pytest.param({**_ALL_ON, "length": 16, "use_digits": "on"}, REQUEST_SCHEMA, id="req-checkbox-string"),
        pytest.param(
            {"length": 16, "use_uppercase": True, "use_lowercase": True, "use_digits": True},
            REQUEST_SCHEMA,
            id="req-sem-use_symbols",
        ),
        pytest.param({**_ALL_ON, "length": 16, "extra": 1}, REQUEST_SCHEMA, id="req-campo-extra"),
        pytest.param([], RESPONSE_200_SCHEMA, id="200-nao-objeto"),
        pytest.param({"password": "Ab1!xyzW"}, RESPONSE_200_SCHEMA, id="200-sem-strength"),
        pytest.param({"password": "Ab1!xyzW", "strength": None}, RESPONSE_200_SCHEMA, id="200-strength-null"),
        pytest.param({"password": 123, "strength": {"label": "Boa", "entropy": 52.0}}, RESPONSE_200_SCHEMA, id="200-password-numero"),
        pytest.param({"password": "x", "strength": {"entropy": 52.0}}, RESPONSE_200_SCHEMA, id="200-sem-label"),
        pytest.param({"password": "x", "strength": {"label": "Media", "entropy": 52.0}}, RESPONSE_200_SCHEMA, id="200-label-fora-enum"),
        pytest.param({"password": "x", "strength": {"label": "Boa"}}, RESPONSE_200_SCHEMA, id="200-sem-entropy"),
        pytest.param({"password": "x", "strength": {"label": "Boa", "entropy": "52.3"}}, RESPONSE_200_SCHEMA, id="200-entropy-string"),
        pytest.param({"password": "x", "strength": {"label": "Boa", "entropy": True}}, RESPONSE_200_SCHEMA, id="200-entropy-bool"),
        pytest.param({"password": "x", "strength": {"label": "Boa", "entropy": -1}}, RESPONSE_200_SCHEMA, id="200-entropy-negativa"),
        pytest.param({"password": "x", "strength": {"label": "Boa", "entropy": 1.0, "score": 6}}, RESPONSE_200_SCHEMA, id="200-score-fora-faixa"),
        pytest.param({}, RESPONSE_400_SCHEMA, id="400-sem-error"),
        pytest.param({"error": None}, RESPONSE_400_SCHEMA, id="400-error-null"),
        pytest.param({"error": ["msg"]}, RESPONSE_400_SCHEMA, id="400-error-lista"),
    ],
)
def test_validador_minimo_detecta_violacoes(instance, schema):
    """INT-C02 — Meta-teste: o validador próprio detecta violações conhecidas.
    Sem isso, um validador com bug deixaria todos os testes de contrato verdes."""
    assert validate(instance, schema), f"Violacao nao detectada: {instance!r}"


@pytest.mark.parametrize(
    "instance, schema",
    [
        pytest.param(
            {"password": "Ab1!xyzW", "strength": {"label": "Boa", "entropy": 52}},
            RESPONSE_200_SCHEMA,
            id="200-entropy-inteira-sem-score",
        ),
        pytest.param(
            {"password": "Ab1!xyzW", "strength": {"label": "Forte", "entropy": 78.5, "score": 4, "x": 1}, "meta": {}},
            RESPONSE_200_SCHEMA,
            id="200-campos-extras",
        ),
        pytest.param(
            {"error": "Selecione ao menos um tipo de caractere.", "code": "NO_CHARSET"},
            RESPONSE_400_SCHEMA,
            id="400-campo-extra",
        ),
    ],
)
def test_validador_minimo_aceita_variacoes_toleradas(instance, schema):
    """INT-C03 — Leitor tolerante: campos extras, `score` ausente e entropia
    inteira não quebram o consumidor e, portanto, não violam o contrato."""
    assert validate(instance, schema) == []


# ---------------------------------------------------------------------------
# Testes: provedor x payloads reais do consumidor — caminho de sucesso
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload", SUCCESS_CASES)
def test_sucesso_retorna_200_conforme_schema(client, payload):
    """INT-C04 — Para todo payload produzível com ao menos um checkbox marcado,
    o provedor responde 200 (response.ok) com corpo válido no schema 200."""
    response = send_like_consumer(client, payload)
    data = read_json_like_browser(response)
    assert response.status_code == 200, f"Status {response.status_code}: {data!r}"
    assert_valid(data, RESPONSE_200_SCHEMA)


@pytest.mark.parametrize("payload", SUCCESS_CASES)
def test_sucesso_campos_lidos_pelo_consumidor_tem_tipo_esperado_pelo_js(client, payload):
    """INT-C05 — Cada campo lido por app.js existe e tem o tipo que o JS espera:
    data.password (string não vazia -> input.value), data.strength (objeto, senão
    TypeError), data.strength.label (string -> textContent) e
    data.strength.entropy (número finito, não booleano), para que
    `${entropy} bits` vire "N bits" e não "undefined bits", "NaN bits",
    "true bits" ou "[object Object] bits"."""
    response = send_like_consumer(client, payload)
    data = read_json_like_browser(response)
    assert response.status_code == 200

    password = data.get("password")
    assert isinstance(password, str) and password, f"data.password invalido: {password!r}"

    strength = data.get("strength")
    assert isinstance(strength, dict), f"data.strength nao e objeto: {strength!r}"

    label = strength.get("label")
    assert isinstance(label, str) and label.strip(), f"data.strength.label invalido: {label!r}"

    entropy = strength.get("entropy")
    assert isinstance(entropy, (int, float)) and not isinstance(entropy, bool), (
        f"data.strength.entropy nao e numero: {entropy!r}"
    )
    assert math.isfinite(entropy) and entropy >= 0, f"entropia invalida: {entropy!r}"


@pytest.mark.parametrize("payload", SUCCESS_CASES)
def test_sucesso_content_type_json(client, payload):
    """INT-C06 — A resposta 200 tem Content-Type application/json, já que o
    consumidor sempre chama response.json()."""
    response = send_like_consumer(client, payload)
    assert response.status_code == 200
    assert_json_content_type(response)


@pytest.mark.parametrize("payload", SUCCESS_CASES)
def test_sucesso_senha_respeita_semantica_do_formulario(client, payload):
    """INT-C07 — Semântica mínima que a UI promete ao usuário: a senha tem o
    comprimento escolhido no slider e não contém classes de caractere cujo
    checkbox foi desmarcado. A presença obrigatória das classes marcadas não
    é verificada, porque o código do provedor não deixa claro se ela é garantida."""
    response = send_like_consumer(client, payload)
    data = read_json_like_browser(response)
    assert response.status_code == 200
    password = data["password"]

    assert len(password) == payload["length"]

    forbidden_by_flag = {
        "use_uppercase": string.ascii_uppercase,
        "use_lowercase": string.ascii_lowercase,
        "use_digits": string.digits,
    }
    for flag, chars in forbidden_by_flag.items():
        if not payload[flag]:
            leaked = set(password) & set(chars)
            assert not leaked, f"{flag}=false, mas a senha contem {sorted(leaked)}"

    if not payload["use_symbols"]:
        alnum = set(string.ascii_letters + string.digits)
        leaked = set(password) - alnum
        assert not leaked, f"use_symbols=false, mas a senha contem {sorted(leaked)}"


# ---------------------------------------------------------------------------
# Testes: provedor x payloads reais do consumidor — caminho de erro
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload", ERROR_CASES)
def test_todos_desmarcados_retorna_400_conforme_schema(client, payload):
    """INT-C08 — Com todos os checkboxes desmarcados (payload que o consumidor
    consegue enviar), o provedor responde 400 com corpo válido no schema de erro,
    sem 200 com senha vazia e sem 500."""
    response = send_like_consumer(client, payload)
    data = read_json_like_browser(response)
    assert response.status_code == 400, f"Status {response.status_code}: {data!r}"
    assert_valid(data, RESPONSE_400_SCHEMA)


@pytest.mark.parametrize("payload", ERROR_CASES)
def test_erro_campo_lido_pelo_consumidor_e_mensagem_util(client, payload):
    """INT-C09 — No erro, response.ok é false e data.error é uma string não
    vazia. Se vier vazia ou ausente, o consumidor cai no fallback genérico
    "Nao foi possivel gerar a senha." e o usuário não sabe o que corrigir."""
    response = send_like_consumer(client, payload)
    data = read_json_like_browser(response)
    assert not (200 <= response.status_code < 300), "response.ok seria true"
    error = data.get("error")
    assert isinstance(error, str) and error.strip(), f"data.error invalido: {error!r}"


@pytest.mark.parametrize("payload", ERROR_CASES)
def test_erro_content_type_json(client, payload):
    """INT-C10 — A resposta 400 também tem Content-Type application/json: o
    consumidor chama response.json() antes de checar response.ok."""
    response = send_like_consumer(client, payload)
    assert response.status_code == 400
    assert_json_content_type(response)
