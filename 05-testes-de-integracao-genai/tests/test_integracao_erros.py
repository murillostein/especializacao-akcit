"""Testes de integração NEGATIVOS e de FRONTEIRA para POST /api/passwords.

Cadeia exercitada sem mocks: rota Flask -> PasswordService -> Config.

Os testes com @pytest.mark.xfail(strict=True) documentam DEFEITOS. Eles afirmam o
comportamento DESEJADO, então hoje "falham como esperado" (XFAIL) e não quebram
o CI. Quando o defeito for corrigido, viram XPASS e, por serem estritos, fazem a
suíte falhar. É o sinal para remover o marcador.

Observação: nos casos que hoje terminam em AttributeError (500), o xfail cobre os
dois cenários possíveis: resposta 500 (app sem TESTING) ou exceção propagada
(app com TESTING/PROPAGATE_EXCEPTIONS).
"""
import json

import pytest

from password_generator import create_app
from password_generator.config import Config

URL = "/api/passwords"

MIN = Config.MIN_PASSWORD_LENGTH
MAX = Config.MAX_PASSWORD_LENGTH
DEFAULT = Config.DEFAULT_PASSWORD_LENGTH

# Mensagens copiadas literalmente de PasswordService._normalize_options
MSG_INTEIRO = "O comprimento da senha deve ser um inteiro."
MSG_MIN = f"O comprimento minimo e {MIN} caracteres."
MSG_MAX = f"O comprimento maximo e {MAX} caracteres."
MSG_GRUPO = "Selecione ao menos um conjunto de caracteres para gerar a senha."

TODAS_FLAGS = ("use_uppercase", "use_lowercase", "use_digits", "use_symbols")


def _flags(valor):
    return {flag: valor for flag in TODAS_FLAGS}


def _post_raw(client, corpo, content_type="application/json"):
    return client.post(URL, data=corpo, content_type=content_type)


def _assert_sucesso(resp, comprimento):
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body["password"], str)
    assert len(body["password"]) == comprimento
    assert "strength" in body


def _assert_erro(resp, mensagem):
    assert resp.status_code == 400
    assert resp.get_json() == {"error": mensagem}


# Subclasses de Config para o item 7 (integração create_app -> serviço)
class ConfigMaxReduzido(Config):
    MAX_PASSWORD_LENGTH = MIN + 2  # 10 com os padrões


class ConfigMinElevado(Config):
    MIN_PASSWORD_LENGTH = MIN + 4  # 12 com os padrões


class ConfigDefaultAlterado(Config):
    DEFAULT_PASSWORD_LENGTH = DEFAULT + 4  # 20 com os padrões


# ---------------------------------------------------------------------------
# 1. Fronteiras de length
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload, comprimento",
    [
        ({"length": MIN}, MIN),
        ({"length": MAX}, MAX),
        ({"length": None}, DEFAULT),
        ({"use_symbols": False}, DEFAULT),
    ],
    ids=["minimo", "maximo", "length_null", "length_ausente"],
)
def test_length_na_fronteira_valida(client, payload, comprimento):
    """INT-E01: valores de fronteira válidos de length geram senha do tamanho certo."""
    resp = client.post(URL, json=payload)
    # Real: int em [MIN, MAX] (ou None -> DEFAULT) passa na validação -> 200.
    _assert_sucesso(resp, comprimento)


@pytest.mark.parametrize(
    "length, mensagem",
    [
        (MIN - 1, MSG_MIN),
        (0, MSG_MIN),
        (-1, MSG_MIN),
        (MAX + 1, MSG_MAX),
        (10**30, MSG_MAX),
    ],
    ids=["abaixo_do_minimo", "zero", "negativo", "acima_do_maximo", "inteiro_gigante"],
)
def test_length_fora_da_fronteira(client, length, mensagem):
    """INT-E02: length fora de [MIN, MAX] é rejeitado com 400 e mensagem do limite."""
    resp = client.post(URL, json={"length": length})
    # Real: int fora do intervalo -> PasswordGenerationError -> 400.
    _assert_erro(resp, mensagem)


# ---------------------------------------------------------------------------
# 2. Tipos errados em length
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "length",
    ["12", "abc", "", 12.0, 12.5, [12], {"valor": 12}],
    ids=[
        "string_numerica",
        "string_texto",
        "string_vazia",
        "float_inteiro",
        "float_fracionario",
        "lista",
        "objeto",
    ],
)
def test_length_tipo_errado(client, length):
    """INT-E03: length de tipo não inteiro é rejeitado com a mensagem de inteiro."""
    resp = client.post(URL, json={"length": length})
    # Real: isinstance(length, int) é False -> 400 com MSG_INTEIRO.
    _assert_erro(resp, MSG_INTEIRO)


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: bool é subclasse de int; length booleano passa na checagem de "
    "tipo e é tratado como 1/0, gerando a mensagem de mínimo em vez da de inteiro",
)
@pytest.mark.parametrize("length", [True, False], ids=["true", "false"])
def test_length_booleano(client, length):
    """INT-E04: length booleano deveria ser rejeitado como não inteiro."""
    resp = client.post(URL, json={"length": length})
    # Real: True==1 / False==0 < MIN -> 400 com MSG_MIN (mensagem enganosa).
    _assert_erro(resp, MSG_INTEIRO)


# ---------------------------------------------------------------------------
# 3. Nenhum grupo selecionado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [_flags(False), {"length": MAX, **_flags(False)}],
    ids=["todas_false", "todas_false_length_maximo"],
)
def test_nenhum_grupo_selecionado(client, payload):
    """INT-E05: sem nenhum conjunto de caracteres a API responde 400."""
    resp = client.post(URL, json=payload)
    # Real: any([False]*4) é False -> 400 com MSG_GRUPO.
    _assert_erro(resp, MSG_GRUPO)


@pytest.mark.parametrize(
    "payload, mensagem",
    [
        ({"length": MIN - 1, **_flags(False)}, MSG_MIN),
        ({"length": "abc", **_flags(False)}, MSG_INTEIRO),
    ],
    ids=["length_invalido_precede_grupos", "tipo_invalido_precede_grupos"],
)
def test_precedencia_da_validacao(client, payload, mensagem):
    """INT-E06: a validação de length acontece antes da validação de grupos."""
    resp = client.post(URL, json=payload)
    # Real: _normalize_options valida tipo -> mínimo -> máximo -> grupos, nessa ordem.
    _assert_erro(resp, mensagem)


# ---------------------------------------------------------------------------
# 4. Flags com tipo errado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "valor",
    [0, "", [], {}],
    ids=["zero", "string_vazia", "lista_vazia", "objeto_vazio"],
)
def test_flags_falsy_de_tipo_errado_sao_rejeitadas(client, valor):
    """INT-E07: flags falsy de tipo não booleano resultam em nenhum grupo -> 400."""
    resp = client.post(URL, json=_flags(valor))
    # Real: valores falsy -> any(...) False -> 400 MSG_GRUPO (só por truthiness).
    _assert_erro(resp, MSG_GRUPO)


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: flags não são validadas como bool; strings como 'false' e '0' "
    "são truthy e ATIVAM o grupo, contrariando a intenção do cliente",
)
@pytest.mark.parametrize(
    "payload",
    [_flags("false"), _flags("0"), {"use_symbols": "false"}],
    ids=["string_false_todas", "string_zero_todas", "apenas_symbols_string_false"],
)
def test_flags_string_sao_rejeitadas(client, payload):
    """INT-E08: flags enviadas como string deveriam ser rejeitadas com 400."""
    resp = client.post(URL, json=payload)
    # Real: strings não vazias são truthy -> grupos ativos -> 200 com senha.
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: flag null é tratada como False (payload.get(k, True) só usa o "
    "padrão se a chave faltar), inconsistente com length null, que usa o padrão",
)
def test_flags_null_usam_padrao(client):
    """INT-E09: flags null deveriam assumir o padrão (True), como ocorre com length null."""
    resp = client.post(URL, json=_flags(None))
    # Real: .get devolve None (falsy) para as 4 flags -> 400 MSG_GRUPO.
    _assert_sucesso(resp, DEFAULT)


# ---------------------------------------------------------------------------
# 5. Corpo malformado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"json": {}},
        {"data": "", "content_type": "application/json"},
    ],
    ids=["sem_corpo_sem_content_type", "objeto_vazio", "corpo_vazio_content_type_json"],
)
def test_corpo_ausente_ou_vazio_usa_padroes(client, kwargs):
    """INT-E10: sem parâmetros, a API gera senha com os valores padrão."""
    resp = client.post(URL, **kwargs)
    # Real: get_json(silent=True) -> None ou {} ; "or {}" -> padrões -> 200.
    _assert_sucesso(resp, DEFAULT)


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: JSON válido mas não-objeto e truthy chega a payload.get -> "
    "AttributeError não tratado -> 500",
)
@pytest.mark.parametrize(
    "corpo",
    ["[8]", '[{"length": 8}]', '"abc"', "42", "true"],
    ids=["lista_com_inteiro", "lista_com_objeto", "string", "numero", "booleano_true"],
)
def test_json_nao_objeto_truthy_retorna_400(client, corpo):
    """INT-E11: corpo JSON que não é objeto deveria ser rejeitado com 400, não 500."""
    resp = _post_raw(client, corpo)
    # Real: list/str/int/bool não têm .get -> AttributeError -> 500.
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: JSON não-objeto falsy é aceito em silêncio ('x or {}' -> {}) e "
    "gera senha com padrões",
)
@pytest.mark.parametrize(
    "corpo",
    ["[]", '""', "0", "false", "null"],
    ids=["lista_vazia", "string_vazia", "zero", "false", "null"],
)
def test_json_nao_objeto_falsy_retorna_400(client, corpo):
    """INT-E12: corpo JSON falsy e não-objeto deveria ser rejeitado com 400."""
    resp = _post_raw(client, corpo)
    # Real: valor falsy -> "or {}" -> {} -> padrões -> 200.
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: get_json(silent=True) engole o erro de sintaxe JSON e a API "
    "responde 200 com padrões",
)
@pytest.mark.parametrize(
    "corpo",
    ['{"length": 8,', "{length: 8}", "{'length': 8}", "nao e json"],
    ids=["json_truncado", "chave_sem_aspas", "aspas_simples", "texto_livre"],
)
def test_json_sintaticamente_invalido_retorna_400(client, corpo):
    """INT-E13: JSON inválido com Content-Type JSON deveria resultar em 400."""
    resp = _post_raw(client, corpo)
    # Real: parse falha em silêncio -> None -> {} -> 200 com len DEFAULT.
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: sem Content-Type JSON o corpo é ignorado em silêncio; um length "
    "inválido escapa da validação e a API devolve 200 com padrões",
)
@pytest.mark.parametrize(
    "content_type",
    [None, "text/plain", "application/x-www-form-urlencoded"],
    ids=["sem_content_type", "text_plain", "form_urlencoded"],
)
def test_corpo_sem_content_type_json_nao_e_ignorado(client, content_type):
    """INT-E14: corpo enviado sem Content-Type JSON deveria ser rejeitado (400/415)."""
    corpo = json.dumps({"length": MIN - 1})
    resp = client.post(URL, data=corpo, content_type=content_type)
    # Real: mimetype não JSON -> get_json silent -> None -> {} -> 200 len DEFAULT.
    assert resp.status_code in (400, 415)


# ---------------------------------------------------------------------------
# 6. Método não suportado e rota inexistente
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("metodo", ["get", "put", "patch", "delete"], ids=["get", "put", "patch", "delete"])
def test_metodo_nao_suportado(client, metodo):
    """INT-E15: métodos diferentes de POST retornam 405 com cabeçalho Allow."""
    resp = getattr(client, metodo)(URL)
    # Real: @web.post registra apenas POST (+ OPTIONS automático) -> 405.
    assert resp.status_code == 405
    assert "POST" in resp.headers["Allow"]


@pytest.mark.parametrize(
    "rota",
    ["/api/password", "/api/passwords/", "/api/passwords/extra", "/api/senhas"],
    ids=["singular", "barra_final", "subrota", "nome_traduzido"],
)
def test_rota_inexistente(client, rota):
    """INT-E16: rotas que não existem retornam 404."""
    resp = client.post(rota, json={})
    # Real: nenhuma regra casa (regra sem barra final não redireciona) -> 404.
    assert resp.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: erros 404/405 da API são devolvidos como HTML, sem o formato "
    "JSON {'error': ...} usado pelo endpoint",
)
@pytest.mark.parametrize(
    "metodo, rota",
    [("get", URL), ("post", "/api/inexistente")],
    ids=["405_get", "404_rota_inexistente"],
)
def test_erros_http_da_api_sao_json(client, metodo, rota):
    """INT-E17: respostas de erro HTTP sob /api deveriam ser JSON."""
    resp = getattr(client, metodo)(rota)
    # Real: handlers padrão do Flask -> text/html.
    assert resp.is_json
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# 7. Integração create_app(config_class=...) -> limites usados pelo serviço
# ---------------------------------------------------------------------------
def test_create_app_carrega_subclasse_de_config():
    """INT-E18: create_app copia os limites da subclasse para app.config."""
    app = create_app(config_class=ConfigMaxReduzido)
    # Real: from_object lê atributos em maiúsculas (inclusive herdados).
    assert app.config["MAX_PASSWORD_LENGTH"] == ConfigMaxReduzido.MAX_PASSWORD_LENGTH
    assert app.config["MIN_PASSWORD_LENGTH"] == MIN


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: PasswordService lê a classe global Config, não current_app.config; "
    "os limites passados a create_app(config_class=...) são ignorados",
)
@pytest.mark.parametrize(
    "config_cls, length, mensagem",
    [
        (
            ConfigMaxReduzido,
            ConfigMaxReduzido.MAX_PASSWORD_LENGTH + 1,
            f"O comprimento maximo e {ConfigMaxReduzido.MAX_PASSWORD_LENGTH} caracteres.",
        ),
        (
            ConfigMinElevado,
            ConfigMinElevado.MIN_PASSWORD_LENGTH - 1,
            f"O comprimento minimo e {ConfigMinElevado.MIN_PASSWORD_LENGTH} caracteres.",
        ),
    ],
    ids=["max_reduzido", "min_elevado"],
)
def test_limites_da_config_do_app_sao_respeitados(config_cls, length, mensagem):
    """INT-E19: o serviço deveria aplicar os limites da Config passada ao app."""
    client = create_app(config_class=config_cls).test_client()
    resp = client.post(URL, json={"length": length})
    # Real: o serviço usa Config.MIN/MAX globais (8/64) -> length aceito -> 200.
    _assert_erro(resp, mensagem)


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: DEFAULT_PASSWORD_LENGTH da Config do app é ignorado; o serviço "
    "usa Config.DEFAULT_PASSWORD_LENGTH global",
)
def test_default_da_config_do_app_e_respeitado():
    """INT-E20: sem length, o serviço deveria usar o DEFAULT da Config do app."""
    client = create_app(config_class=ConfigDefaultAlterado).test_client()
    resp = client.post(URL, json={})
    # Real: length None -> Config.DEFAULT_PASSWORD_LENGTH global (16) -> len 16.
    _assert_sucesso(resp, ConfigDefaultAlterado.DEFAULT_PASSWORD_LENGTH)
