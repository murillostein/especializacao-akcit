# Prompts utilizados

Este documento registra, **na íntegra**, os prompts enviados à LLM. Cada prompt foi executado em uma sessão isolada (sem histórico, sem acesso ao repositório e sem ferramentas), para que a resposta dependesse apenas do texto do prompt. As respostas brutas estão em [`saidas-llm/`](saidas-llm/).

- **LLM utilizada**: Claude (Anthropic), via Claude Code
- **Data dos experimentos**: 25/10/2026

| Prompt | Tipo | Versão | Saída bruta |
|---|---|---|---|
| P1 | Geração de cenários de integração (caminho de sucesso) | v1 – genérico | [`p1-v1-cenarios.md`](saidas-llm/p1-v1-cenarios.md) |
| P1 | Geração de cenários de integração (caminho de sucesso) | v2 – refinado | [`p1-v2-cenarios.md`](saidas-llm/p1-v2-cenarios.md) |
| P2 | Casos de erro e dados de teste (negativos e de fronteira) | v1 – genérico | [`p2-v1-erros.md`](saidas-llm/p2-v1-erros.md) |
| P2 | Casos de erro e dados de teste (negativos e de fronteira) | v2 – refinado | [`p2-v2-erros.md`](saidas-llm/p2-v2-erros.md) |
| P3 | Contrato de API orientado ao consumidor (front-end ↔ back-end) | v2 – já refinado | [`p3-contrato.md`](saidas-llm/p3-contrato.md) |

O P3 foi escrito já na forma refinada, aplicando direto o que se aprendeu com a v1 de P1 e P2.

---

## P1 v1 – Cenários de integração (genérico)

```text
Gere casos de teste de integração para uma API REST de geração de senhas feita em Flask.
```

## P2 v1 – Casos de erro (genérico)

```text
Gere casos de teste de integração com dados inválidos e casos de erro para uma API de geração de senhas em Flask.
```

---

## P1 v2 – Cenários de integração (refinado)

````text
## Papel
Atue como engenheiro(a) de testes especialista em testes de integração de APIs Flask.

## Contexto do sistema
Aplicação Flask de página única que gera senhas. Não há banco de dados, autenticação nem chamadas externas (decisão de negócio: a senha nunca é persistida). O fluxo integrado é:

Frontend (app.js) --POST /api/passwords (JSON)--> rota Flask (routes.py) --> PasswordService.generate / evaluate_strength --> Config (limites e padrão de comprimento)

Código real (Python 3.12, Flask 3.1, pytest 8.3):

```python
# password_generator/__init__.py
def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.register_blueprint(web)
    return app

# password_generator/config.py
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key")
    DEFAULT_PASSWORD_LENGTH = int(os.getenv("DEFAULT_PASSWORD_LENGTH", "16"))
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_PASSWORD_LENGTH = int(os.getenv("MAX_PASSWORD_LENGTH", "64"))

# password_generator/routes.py
@web.get("/")
def index():
    return render_template("index.html")   # página contém o texto "Gerador de Senhas"

@web.post("/api/passwords")
def generate_password():
    payload = request.get_json(silent=True) or {}
    try:
        password = PasswordService.generate(
            length=payload.get("length"),
            use_uppercase=payload.get("use_uppercase", True),
            use_lowercase=payload.get("use_lowercase", True),
            use_digits=payload.get("use_digits", True),
            use_symbols=payload.get("use_symbols", True),
        )
    except PasswordGenerationError as exc:
        return jsonify({"error": str(exc)}), 400
    strength = PasswordService.evaluate_strength(password)
    return jsonify({"password": password, "strength": strength})

# password_generator/services/password_service.py (trechos)
class PasswordService:
    UPPERCASE = string.ascii_uppercase
    LOWERCASE = string.ascii_lowercase
    DIGITS = string.digits
    SYMBOLS = "!@#$%&*()-_=+[]{};:,.?/|"

    @classmethod
    def generate(cls, length, use_uppercase, use_lowercase, use_digits, use_symbols) -> str:
        # length None -> Config.DEFAULT_PASSWORD_LENGTH
        # valida: int, MIN <= length <= MAX, ao menos um grupo; garante 1 caractere de cada grupo
        # selecionado; usa secrets.choice + SystemRandom().shuffle
        ...

    @classmethod
    def evaluate_strength(cls, password: str) -> dict:
        # pool = soma dos tamanhos dos grupos presentes na senha (26, 26, 10, 24)
        # entropy = round(len(password) * log2(pool), 2)
        # <40 "Muito fraca"/1, <60 "Fraca"/2, <80 "Boa"/3, <100 "Forte"/4, senão "Muito forte"/5
        ...
```

## Tarefa
Gere cenários de teste de integração do CAMINHO DE SUCESSO que exercitem a cadeia completa HTTP → rota → PasswordService → Config, usando `app.test_client()`. Cubra no mínimo:
1. cada grupo de caracteres isolado e a combinação de todos;
2. aplicação do comprimento padrão vindo de Config quando `length` é omitido ou `null`;
3. limites válidos (mínimo e máximo exatos);
4. coerência entre a senha devolvida e o objeto `strength` (recalcule a entropia esperada no teste, a partir da senha recebida);
5. a garantia de que cada grupo selecionado aparece ao menos uma vez;
6. ausência de repetição entre chamadas consecutivas (sem estado compartilhado);
7. a página `/` sendo servida pela mesma aplicação.

## Restrições
- pytest + Flask test client. Considere que já existe em `conftest.py` uma fixture `client` (retorna `create_app().test_client()`). Não crie servidor real.
- NÃO faça mock de PasswordService nem de Config: o objetivo é testar as camadas reais juntas.
- NÃO invente endpoints, campos de JSON ou mensagens que não existam no código acima.
- Use `pytest.mark.parametrize` quando o mesmo fluxo variar só nos dados.
- Cada teste deve ter docstring com um ID no formato `INT-Fxx` e seguir Arrange / Act / Assert.
- No máximo 12 funções de teste.

## Formato da resposta
1. Uma tabela Markdown: ID | Objetivo | Entrada | Resultado esperado.
2. Um único bloco de código com o arquivo completo `test_integracao_fluxos.py`, pronto para rodar.
3. Uma lista curta de premissas que você assumiu e que eu devo validar.
````

---

## P2 v2 – Casos de erro e dados de teste (refinado)

````text
## Papel
Atue como engenheiro(a) de testes especialista em testes negativos e robustez de APIs REST.

## Contexto do sistema
Aplicação Flask que gera senhas. Sem banco, sem autenticação, sem serviços externos. Fluxo: POST /api/passwords (JSON) → rota → PasswordService → Config.

Código real (Python 3.12, Flask 3.1, pytest 8.3):

```python
# password_generator/__init__.py
def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.register_blueprint(web)
    return app

# password_generator/config.py
class Config:
    DEFAULT_PASSWORD_LENGTH = int(os.getenv("DEFAULT_PASSWORD_LENGTH", "16"))
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_PASSWORD_LENGTH = int(os.getenv("MAX_PASSWORD_LENGTH", "64"))

# password_generator/routes.py
@web.post("/api/passwords")
def generate_password():
    payload = request.get_json(silent=True) or {}
    try:
        password = PasswordService.generate(
            length=payload.get("length"),
            use_uppercase=payload.get("use_uppercase", True),
            use_lowercase=payload.get("use_lowercase", True),
            use_digits=payload.get("use_digits", True),
            use_symbols=payload.get("use_symbols", True),
        )
    except PasswordGenerationError as exc:
        return jsonify({"error": str(exc)}), 400
    strength = PasswordService.evaluate_strength(password)
    return jsonify({"password": password, "strength": strength})

# password_generator/services/password_service.py
class PasswordGenerationError(ValueError):
    pass

class PasswordService:
    @classmethod
    def generate(cls, length, use_uppercase, use_lowercase, use_digits, use_symbols) -> str:
        options = cls._normalize_options(PasswordOptions(
            length=length if length is not None else Config.DEFAULT_PASSWORD_LENGTH,
            use_uppercase=use_uppercase, use_lowercase=use_lowercase,
            use_digits=use_digits, use_symbols=use_symbols))
        ...

    @classmethod
    def _normalize_options(cls, options):
        if not isinstance(options.length, int):
            raise PasswordGenerationError("O comprimento da senha deve ser um inteiro.")
        if options.length < Config.MIN_PASSWORD_LENGTH:
            raise PasswordGenerationError(f"O comprimento minimo e {Config.MIN_PASSWORD_LENGTH} caracteres.")
        if options.length > Config.MAX_PASSWORD_LENGTH:
            raise PasswordGenerationError(f"O comprimento maximo e {Config.MAX_PASSWORD_LENGTH} caracteres.")
        if not any([options.use_uppercase, options.use_lowercase, options.use_digits, options.use_symbols]):
            raise PasswordGenerationError("Selecione ao menos um conjunto de caracteres para gerar a senha.")
        return options
```

## Tarefa
Gere casos de teste de integração NEGATIVOS e de dados de fronteira para `POST /api/passwords`, exercitando a cadeia real rota → serviço → Config. Cubra, no mínimo:
1. valores de fronteira de `length` (abaixo do mínimo, mínimo, máximo, acima do máximo, zero, negativo);
2. tipos errados em `length` (string numérica, float, booleano, lista, objeto);
3. nenhum grupo selecionado;
4. flags enviadas com tipo errado (ex.: string "false", 0, null);
5. corpo malformado: não-JSON, JSON vazio `{}`, JSON que é uma lista, JSON que é uma string, sem Content-Type;
6. método HTTP não suportado no endpoint e rota inexistente;
7. a integração entre `create_app(config_class=...)` e os limites usados pelo serviço (ex.: uma subclasse de Config com MAX_PASSWORD_LENGTH diferente).

## Regras de raciocínio (importante)
- Antes de escrever cada assert, DERIVE do código acima qual é o comportamento REAL (status HTTP e corpo). Explique em uma linha.
- Se o comportamento real for, na sua análise, um defeito (ex.: erro 500, aceitação silenciosa de dado inválido, configuração ignorada), escreva o teste afirmando o comportamento DESEJADO e marque-o com `@pytest.mark.xfail(strict=True, reason="DEFEITO: <descrição>")`. Assim a suíte documenta o defeito sem quebrar o CI, e passa a falhar quando o defeito for corrigido.
- Lembre-se de detalhes de Python: `bool` é subclasse de `int`; `[] or {}` e `"" or {}` resultam em `{}`; listas e strings não têm `.get`.
- Não invente mensagens de erro: use apenas as que estão no código.

## Restrições
- pytest + Flask test client; já existe em `conftest.py` a fixture `client` (`create_app().test_client()`). Para o item 7, crie o app dentro do próprio teste.
- Sem mocks de PasswordService/Config.
- Use `pytest.mark.parametrize` com `ids=` legíveis para os dados de teste.
- Cada teste com docstring contendo um ID `INT-Exx`.

## Formato da resposta
1. Tabela Markdown: ID | Entrada | Comportamento real derivado do código | Esperado | Defeito? (sim/não).
2. Um único bloco de código com o arquivo completo `test_integracao_erros.py`.
3. Lista dos defeitos encontrados, em ordem de severidade.
````

---

## P3 – Contrato de API orientado ao consumidor

````text
## Papel
Atue como engenheiro(a) de testes especializado(a) em testes de contrato orientados ao consumidor (consumer-driven contracts).

## Contexto
O consumidor é o frontend JavaScript e o provedor é uma API Flask. Os dois lados estão abaixo; o contrato NÃO está documentado em lugar nenhum, então ele deve ser inferido do código dos dois lados.

Consumidor (`static/js/app.js`, trecho relevante):
```javascript
// <input id="length" name="length" type="range" min="8" max="64" value="16" />
// 4 checkboxes: use_uppercase, use_lowercase, use_digits, use_symbols (todos marcados por padrão)
const formData = new FormData(form);
const payload = {
  length: Number(formData.get("length")),
  use_uppercase: formData.get("use_uppercase") === "on",
  use_lowercase: formData.get("use_lowercase") === "on",
  use_digits: formData.get("use_digits") === "on",
  use_symbols: formData.get("use_symbols") === "on",
};
const response = await fetch("/api/passwords", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});
const data = await response.json();
if (!response.ok) {
  feedback.textContent = data.error || "Nao foi possivel gerar a senha.";
  return;
}
passwordOutput.value = data.password;
strengthLabel.textContent = data.strength.label;
entropyValue.textContent = `${data.strength.entropy} bits`;
```

Provedor (`routes.py` e serviço, trechos):
```python
@web.post("/api/passwords")
def generate_password():
    payload = request.get_json(silent=True) or {}
    try:
        password = PasswordService.generate(
            length=payload.get("length"),
            use_uppercase=payload.get("use_uppercase", True),
            use_lowercase=payload.get("use_lowercase", True),
            use_digits=payload.get("use_digits", True),
            use_symbols=payload.get("use_symbols", True),
        )
    except PasswordGenerationError as exc:
        return jsonify({"error": str(exc)}), 400
    strength = PasswordService.evaluate_strength(password)
    return jsonify({"password": password, "strength": strength})

# evaluate_strength retorna {"label": str, "score": int (0-5), "entropy": float}
# rótulos possíveis: "Muito fraca", "Fraca", "Boa", "Forte", "Muito forte"
# limites de length em Config: MIN 8, MAX 64, padrão 16
```

## Tarefa
1. Escreva o contrato inferido como JSON Schema (draft 2020-12) para: requisição, resposta 200 e resposta 400. Marque como `required` apenas os campos que o CONSUMIDOR realmente lê ou envia.
2. Escreva testes de contrato em pytest que:
   - enviem ao provedor exatamente os payloads que o consumidor consegue produzir (o slider só gera inteiros de 8 a 64 e os checkboxes só geram booleanos) — use uma amostra representativa, incluindo todos os checkboxes desmarcados;
   - validem cada resposta real contra o schema correspondente;
   - verifiquem que todo campo lido pelo consumidor existe e tem o tipo que o JavaScript espera (ex.: `data.strength.entropy` precisa ser número para virar texto "N bits");
   - verifiquem o header `Content-Type: application/json` nas respostas (o consumidor sempre chama `response.json()`, inclusive em erro).
3. Liste divergências ou riscos do contrato (coisas que o provedor aceita/retorna e o consumidor não trata, ou vice-versa).

## Restrições
- Sem bibliotecas além de Flask e pytest (NÃO use `jsonschema`): escreva um validador mínimo próprio, suficiente apenas para os schemas que você definiu (type, required, properties, enum, minimum, maximum, additionalProperties).
- Os schemas devem ficar como dicionários Python no próprio arquivo de teste.
- Já existe em `conftest.py` a fixture `client` (`create_app().test_client()`).
- Cada teste com docstring contendo um ID `INT-Cxx`.

## Formato da resposta
1. Os três schemas em JSON.
2. Um único bloco de código com o arquivo completo `test_contrato_api.py`.
3. Lista de divergências/riscos do contrato.
````
