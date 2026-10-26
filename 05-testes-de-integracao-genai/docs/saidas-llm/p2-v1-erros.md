# Saída bruta – P2 v1 (casos de erro, prompt genérico)

> Resposta da LLM copiada **sem edição**. Prompt na seção "P2 v1" de [`../prompts.md`](../prompts.md). Execução isolada, sem acesso ao repositório.

Seguem testes de integração em **pytest** que usam o `test_client` do Flask. Eles cobrem dados inválidos, erros de protocolo HTTP, limites de tamanho, segurança das respostas de erro e falhas internas.

## Premissas sobre o contrato da API

Ajuste as constantes no topo do arquivo se a sua API for diferente.

| Item | Valor assumido |
|---|---|
| Endpoint | `POST /api/generate` |
| Corpo | JSON `{"length": int, "uppercase": bool, "lowercase": bool, "digits": bool, "symbols": bool}` |
| Faixa de `length` | 4 a 128 |
| Sucesso | `200` com `{"password": "..."}` |
| Erro | JSON `{"error": "mensagem"}`, nunca HTML nem stack trace |
| Política de validação | Estrita: tipos exatos e campos desconhecidos rejeitados |

## Mapa dos casos de teste

| Categoria | Exemplos | Status esperado |
|---|---|---|
| Corpo malformado | JSON quebrado, vazio, raiz que não é objeto, UTF-8 inválido, `NaN`/`Infinity` | 400 |
| Content-Type errado | `text/plain`, formulário, requisição sem corpo | 400 / 415 |
| `length` inválido | 0, negativo, fora da faixa, string, float, `true`, `null`, lista, chave duplicada, inteiro gigante | 400 |
| Flags inválidas | `"true"`, `1`, `null`, todas as flags `false` | 400 |
| Campos desconhecidos | `{"lenght": 20}` (erro de digitação) | 400 |
| Método/rota | GET/PUT/PATCH/DELETE, rota inexistente | 405 / 404 (em JSON) |
| Tamanho | Corpo acima de `MAX_CONTENT_LENGTH`, JSON muito aninhado | 413 / 400 |
| Segurança | Entrada com `<script>` não pode voltar na resposta, sem traceback | 400 |
| Erro interno | Exceção dentro do gerador | 500 genérico |
| Resiliência | A API continua funcionando depois de vários erros | 200 |

## `tests/conftest.py`

```python
import pytest
from app import create_app  # ajuste para a sua factory


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        MAX_CONTENT_LENGTH=16 * 1024,  # 16 KB: suficiente para a API
    )
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
```

## `tests/integration/test_api_erros.py`

```python
import itertools
import json

import pytest

# ---------------------------------------------------------------------------
# Configuração do contrato (ajuste conforme sua API)
# ---------------------------------------------------------------------------
ENDPOINT = "/api/generate"
MIN_LEN, MAX_LEN = 4, 128
FLAGS = ("uppercase", "lowercase", "digits", "symbols")
# Caminho onde a ROTA importa o gerador (faça o patch onde a função é usada)
GENERATOR_PATH = "app.routes.generate_password"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def payload_valido(**overrides):
    base = {"length": 16, "uppercase": True, "lowercase": True,
            "digits": True, "symbols": True}
    base.update(overrides)
    return base


def post_raw(client, data, content_type="application/json"):
    return client.post(ENDPOINT, data=data, content_type=content_type)


def assert_erro(resp, status):
    """Valida o formato padrão de erro: status, JSON, mensagem e sem vazamentos."""
    esperados = status if isinstance(status, tuple) else (status,)
    texto = resp.get_data(as_text=True)

    assert resp.status_code in esperados, f"{resp.status_code}: {texto[:300]}"
    assert resp.is_json, f"Erro deveria ser JSON, veio {resp.content_type}"

    corpo = resp.get_json()
    assert isinstance(corpo.get("error"), str) and corpo["error"].strip()
    assert "password" not in corpo, "Resposta de erro não pode conter senha"
    assert "Traceback" not in texto
    assert 'File "' not in texto  # caminhos de arquivo do stack trace
    return corpo


# ---------------------------------------------------------------------------
# 1. Corpo da requisição malformado
# ---------------------------------------------------------------------------
class TestCorpoMalformado:

    @pytest.mark.parametrize("corpo", [
        '{"length": 12',          # chave de fechamento ausente
        '{length: 12}',           # chave sem aspas
        "{'length': 12}",         # aspas simples
        '{"length": 12,}',        # vírgula sobrando
        "",                       # corpo vazio
        "   ",                    # só espaços
    ], ids=["sem-fechamento", "chave-sem-aspas", "aspas-simples",
            "virgula-final", "vazio", "espacos"])
    def test_json_sintaticamente_invalido(self, client, corpo):
        assert_erro(post_raw(client, corpo), 400)

    @pytest.mark.parametrize("corpo", ["[]", "[16]", '"texto"', "42", "null", "true"])
    def test_raiz_do_json_nao_e_objeto(self, client, corpo):
        assert_erro(post_raw(client, corpo), 400)

    def test_utf8_invalido(self, client):
        assert_erro(post_raw(client, b'{"length": "\xff\xfe"}'), 400)

    @pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
    def test_literais_nao_padrao_do_json(self, client, literal):
        # O json.loads do Python ACEITA NaN/Infinity por padrão. Como
        # NaN < 4 e NaN > 128 são ambos False, uma checagem de faixa ingênua deixa passar.
        assert_erro(post_raw(client, f'{{"length": {literal}}}'), 400)

    def test_json_profundamente_aninhado_nao_gera_500(self, client):
        profundidade = 2000
        corpo = '{"a":' * profundidade + "1" + "}" * profundidade
        # RecursionError não é ValueError: o Flask não o converte em 400 sozinho
        assert_erro(post_raw(client, corpo), (400, 413))


# ---------------------------------------------------------------------------
# 2. Content-Type incorreto
# ---------------------------------------------------------------------------
class TestContentType:

    def test_sem_corpo_e_sem_content_type(self, client):
        assert_erro(client.post(ENDPOINT), (400, 415))

    def test_json_enviado_como_text_plain(self, client):
        resp = post_raw(client, json.dumps(payload_valido()), "text/plain")
        assert_erro(resp, (400, 415))

    def test_dados_de_formulario(self, client):
        resp = client.post(ENDPOINT, data={"length": "16"})
        assert_erro(resp, (400, 415))


# ---------------------------------------------------------------------------
# 3. Campo "length" inválido
# ---------------------------------------------------------------------------
class TestLengthInvalido:

    @pytest.mark.parametrize("valor", [
        0, -1, MIN_LEN - 1, MAX_LEN + 1, 10**9, -10**9,   # faixa
        "16", "", "abc", "16abc",                         # strings
        12.5, 16.0,                                       # floats (16.0: política estrita)
        True, False,                                      # bool é subclasse de int!
        None, [], {}, [16], {"valor": 16},                # outros tipos
    ], ids=repr)
    def test_valores_invalidos(self, client, valor):
        corpo = assert_erro(client.post(ENDPOINT, json=payload_valido(length=valor)), 400)
        # A mensagem deve indicar qual campo falhou
        assert "length" in corpo["error"].lower()

    def test_true_nao_e_aceito_como_inteiro(self, client):
        # Bug clássico: isinstance(True, int) == True, e True vira length=1
        assert_erro(client.post(ENDPOINT, json=payload_valido(length=True)), 400)

    def test_chave_duplicada_valida_o_ultimo_valor(self, client):
        # json.loads mantém o ÚLTIMO valor, que precisa passar pela validação
        assert_erro(post_raw(client, '{"length": 16, "length": 5000}'), 400)

    def test_inteiro_gigante_nao_gera_500(self, client):
        # No Python 3.11+, inteiros com mais de 4300 dígitos geram ValueError
        corpo = '{"length": 1' + "0" * 5000 + "}"
        assert_erro(post_raw(client, corpo), 400)

    @pytest.mark.parametrize("valor", [MIN_LEN, MAX_LEN])
    def test_limites_validos_contraste(self, client, valor):
        """Controle positivo: garante que os limites inválidos acima são os corretos."""
        resp = client.post(ENDPOINT, json=payload_valido(length=valor))
        assert resp.status_code == 200
        assert len(resp.get_json()["password"]) == valor


# ---------------------------------------------------------------------------
# 4. Flags de conjuntos de caracteres inválidas
# ---------------------------------------------------------------------------
VALORES_FLAG_INVALIDOS = ["true", "false", "sim", 1, 0, None, [], {}]


class TestFlagsInvalidas:

    @pytest.mark.parametrize(
        "flag,valor",
        list(itertools.product(FLAGS, VALORES_FLAG_INVALIDOS)),
        ids=repr,
    )
    def test_flag_com_tipo_errado(self, client, flag, valor):
        corpo = assert_erro(client.post(ENDPOINT, json=payload_valido(**{flag: valor})), 400)
        assert flag in corpo["error"].lower()

    def test_todas_as_flags_desativadas(self, client):
        payload = payload_valido(**{f: False for f in FLAGS})
        # Alguns times preferem 422 aqui: ajuste para refletir o contrato
        assert_erro(client.post(ENDPOINT, json=payload), 400)


# ---------------------------------------------------------------------------
# 5. Campos desconhecidos (política estrita)
# ---------------------------------------------------------------------------
class TestCamposDesconhecidos:

    @pytest.mark.parametrize("extra", [
        {"lenght": 20},          # erro de digitação: o cliente acha que pediu 20
        {"admin": True},
        {"__proto__": {}},
    ], ids=repr)
    def test_campo_extra_rejeitado(self, client, extra):
        payload = {**payload_valido(), **extra}
        assert_erro(client.post(ENDPOINT, json=payload), 400)


# ---------------------------------------------------------------------------
# 6. Método HTTP e rota
# ---------------------------------------------------------------------------
class TestHttp:

    @pytest.mark.parametrize("metodo", ["get", "put", "patch", "delete"])
    def test_metodo_nao_permitido(self, client, metodo):
        resp = getattr(client, metodo)(ENDPOINT)
        assert_erro(resp, 405)
        # A RFC 9110 exige o header Allow. Um handler customizado que
        # devolve só jsonify(...) costuma perder esse header.
        assert "POST" in resp.headers.get("Allow", "")

    def test_rota_inexistente_retorna_json(self, client):
        assert_erro(client.post("/api/nao-existe", json=payload_valido()), 404)


# ---------------------------------------------------------------------------
# 7. Limites de tamanho
# ---------------------------------------------------------------------------
class TestTamanhoPayload:

    def test_corpo_acima_do_max_content_length(self, app, client):
        limite = app.config["MAX_CONTENT_LENGTH"]
        corpo = json.dumps({"length": 16, "lixo": "x" * (limite + 1)})
        assert_erro(post_raw(client, corpo), 413)


# ---------------------------------------------------------------------------
# 8. Segurança das respostas de erro
# ---------------------------------------------------------------------------
class TestSegurancaRespostas:

    def test_entrada_maliciosa_nao_e_refletida(self, client):
        ataque = "<script>alert(1)</script>"
        resp = client.post(ENDPOINT, json=payload_valido(length=ataque))
        assert_erro(resp, 400)
        assert ataque not in resp.get_data(as_text=True)

    def test_erro_tem_content_type_json(self, client):
        resp = post_raw(client, "{")
        assert resp.mimetype == "application/json"


# ---------------------------------------------------------------------------
# 9. Erro interno inesperado
# ---------------------------------------------------------------------------
class TestErroInterno:

    def test_excecao_no_gerador_retorna_500_generico(self, app, client, monkeypatch):
        # Com TESTING=True o Flask propaga a exceção em vez de chamar o handler de 500
        app.config["PROPAGATE_EXCEPTIONS"] = False

        def explode(*args, **kwargs):
            raise RuntimeError("detalhe-interno-secreto")

        monkeypatch.setattr(GENERATOR_PATH, explode)

        resp = client.post(ENDPOINT, json=payload_valido())
        assert_erro(resp, 500)
        assert "detalhe-interno-secreto" not in resp.get_data(as_text=True)


# ---------------------------------------------------------------------------
# 10. Resiliência
# ---------------------------------------------------------------------------
class TestResiliencia:

    def test_api_continua_funcional_apos_sequencia_de_erros(self, client):
        for corpo in ("{", "[]", '{"length": -1}', '{"length": NaN}', ""):
            post_raw(client, corpo)

        resp = client.post(ENDPOINT, json=payload_valido(length=20))
        assert resp.status_code == 200
        assert len(resp.get_json()["password"]) == 20
```

## O que a implementação precisa ter para estes testes passarem

1. **Validação estrita de tipos**:
   - Use `type(v) is int`, não `isinstance(v, int)`, para que `True` e `False` sejam rejeitados.
   - Use `type(v) is bool` nas flags.
2. **Rejeição de NaN/Infinity**: valide com `math.isfinite`, ou rejeite qualquer valor que não seja `int`.
3. **Leitura segura do JSON**: use `request.get_json(silent=True)` e retorne 400 se o resultado for `None` ou não for `dict`.
4. **Handlers de erro em JSON** para 400, 404, 405, 413, 415 e 500. No 405, preserve o header `Allow`, por exemplo partindo de `e.get_response()`.
5. **`MAX_CONTENT_LENGTH`** configurado no app.
6. **Captura de `RecursionError`** ao fazer o parse do JSON, devolvendo 400.
7. **Mensagens de erro genéricas**: nada de `str(exception)` nem eco do valor recebido.

## Como executar

```bash
pip install pytest pytest-cov
pytest tests/integration -v
pytest tests/integration --cov=app --cov-report=term-missing
```

Os testes marcados como "política estrita" (float `16.0`, flag `null`, campos extras) são decisões de contrato. Se a sua API for mais permissiva nesses pontos, inverta a asserção ou remova o caso, e deixe a decisão registrada na documentação da API.
