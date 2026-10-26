# Prompts para Testes de Integração com GenAI - Gerador de Senhas

## Contexto

Este módulo aplica os conceitos da Unidade III (tipos de prompt e uso de GenAI em testes unitários, de integração e de sistema) ao mesmo projeto prático dos módulos anteriores (`01-projeto-pratico`). A proposta foi definir tipos de prompt diferentes para apoiar testes de integração, executá-los numa LLM, registrar os casos gerados e comparar como cada prompt, e cada ajuste feito nele, influenciou a qualidade e a diversidade dos testes.

## Cenário de integração

**Integração front-end ↔ back-end REST e entre as camadas internas do back-end** do Gerador de Senhas (Python 3.11+/Flask):

```text
app.js (fetch) --POST /api/passwords JSON--> routes.py --> PasswordService --> Config
     ^                                            |
     '------------- 200 {password, strength} / 400 {error} ------------'
```

Três pontos de integração foram exercitados:

1. **Contrato HTTP** entre o consumidor (`static/js/app.js`) e o provedor (`routes.py`).
2. **Rota → serviço**: tradução do JSON para os parâmetros de `PasswordService` e das exceções para status HTTP.
3. **Aplicação → configuração**: `create_app(config_class)` versus os limites que o serviço realmente aplica.

Todos os testes usam o `test_client` do Flask com as camadas reais, **sem mocks**. O `conftest.py` importa o código diretamente de `01-projeto-pratico`, sem copiá-lo.

## Estrutura dos artefatos

```text
05-testes-de-integracao-genai/
|-- README.md                               (este arquivo: análise e respostas do fórum)
|-- pytest.ini
|-- docs/
|   |-- prompts.md                          (texto integral dos 5 prompts)
|   |-- casos-de-teste.md                   (catálogo dos casos com ID, origem e status)
|   `-- saidas-llm/                         (respostas brutas da LLM, sem edição)
|       |-- p1-v1-cenarios.md
|       |-- p1-v2-cenarios.md
|       |-- p2-v1-erros.md
|       |-- p2-v2-erros.md
|       `-- p3-contrato.md
`-- tests/
    |-- conftest.py                         (fixtures app/client apontando para 01-projeto-pratico)
    |-- test_integracao_fluxos.py           (P1 v2 - cenários de sucesso)
    |-- test_integracao_erros.py            (P2 v2 - erros e dados de fronteira)
    |-- test_contrato_api.py                (P3 - contrato consumidor/provedor)
    `-- test_integracao_complementares.py   (curadoria das ideias úteis das saídas v1)
```

## Como executar

```bash
pip install -r ../01-projeto-pratico/requirements.txt
cd 05-testes-de-integracao-genai
pytest -rx        # -rx lista os defeitos documentados (xfail)
```

Resultado atual: **577 passed, 34 xfailed**. Cada `xfail` é um defeito real confirmado, marcado com `strict=True`. Quando o defeito for corrigido, o teste vira XPASS e a suíte falha, sinalizando que o marcador deve ser removido.

## Metodologia

1. Defini **três tipos de prompt**, cada um com um objetivo diferente de teste de integração.
2. Para P1 e P2, escrevi primeiro uma **versão genérica (v1)**, de uma linha, e depois uma **versão refinada (v2)**. O P3 já nasceu refinado, aplicando o que aprendi com as v1.
3. Executei cada prompt em **sessão isolada da LLM** (Claude, via Claude Code), sem histórico, sem acesso ao repositório e sem ferramentas. Assim, a resposta dependeu só do texto do prompt.
4. Rodei o código gerado **sem nenhuma edição** contra a aplicação real e registrei o resultado.
5. Fiz a **curadoria**: confirmei, executando a API, cada defeito alegado e aproveitei as boas ideias das v1 num arquivo à parte.

| Prompt | Tipo | Objetivo |
|---|---|---|
| **P1** | Geração de cenários de integração | Fluxos de sucesso atravessando rota → serviço → Config |
| **P2** | Casos de erro e dados de teste | Entradas inválidas, fronteiras, corpo malformado, falhas de configuração |
| **P3** | Contrato de API (consumer-driven) | Inferir o contrato a partir do `app.js` e do `routes.py` e validar respostas reais contra ele |

Texto completo dos prompts em [`docs/prompts.md`](docs/prompts.md).

## Resultados por prompt

| Prompt | Casos gerados | Rodam sem edição contra o sistema real | Defeitos reais apontados (confirmados) | Invenções |
|---|---|---|---|---|
| P1 v1 (genérico) | 66 | **2 / 66** passam (endpoint inexistente) | — | endpoint `/api/generate`, campos `uppercase`..., geração em lote (`count`), `/health`, limite 128 |
| P2 v1 (genérico) | 90 | **0 / 90** passam | — | endpoint, limites 4–128, mensagens de erro contendo o nome do campo, `monkeypatch` em módulo inexistente |
| P1 v2 (refinado) | 34 | **34 / 34** | 0 (esperado: são só caminhos de sucesso) | nenhuma |
| P2 v2 (refinado) | 64 | **64 / 64** (36 passam + 28 xfail) | **8 / 8** | nenhuma |
| P3 (contrato) | 499 | **499 / 499** | 0 por teste; 14 riscos listados (13 procedentes) | 1 afirmação incorreta (ver abaixo) |
| Curadoria das v1 | 14 | 14 / 14 (8 passam + 6 xfail) | **6 novos** | — |

Como teste extra, fiz uma "adaptação barata" das v1: troquei apenas o endpoint e os nomes dos campos. Mesmo assim, só **35/66** (P1 v1) e **9/90** (P2 v1) passaram. O problema é que cada falha restante mistura defeito real e premissa inventada, e separar uma da outra exigiu triagem manual, caso a caso.

## Como cada tipo de prompt influenciou a qualidade e a diversidade dos casos

**P1 – Cenários de integração.**
- **Na v1**, a LLM gerou uma suíte "de livro": caminho feliz, aleatoriedade, concorrência, cabeçalhos de segurança, logs. A diversidade foi **alta**, mas a suíte era **inútil como está**, porque tudo foi escrito contra uma API imaginária.
- **Na v2**, a diversidade de categorias **caiu** (só caminho de sucesso, como pedido), mas a **profundidade subiu muito**. A LLM recalculou a entropia no próprio teste a partir da senha recebida (INT-F04), cobriu as 15 combinações de grupos (INT-F05) e checou ausência de estado entre requisições (INT-F07).
- **Sozinho, este tipo de prompt não encontrou nenhum defeito**, o que é esperado. Ele dá confiança de que o fluxo funciona, não de que o sistema é robusto.

**P2 – Casos de erro e dados de teste.**
- Foi o tipo de prompt de **maior valor**. A v2 encontrou **8 defeitos reais**, todos confirmados executando a API. O mais grave: `create_app(config_class=...)` carrega os limites em `app.config`, mas o `PasswordService` lê a classe global `Config`. Ou seja, a configuração por ambiente **não funciona** (INT-E19/E20).
- Outros defeitos encontrados: **500** com corpo JSON do tipo lista (INT-E11), e `use_symbols: "false"` (string) **ligando** os símbolos (INT-E08).
- A **v1 foi mais criativa nos dados de teste**: `NaN`, inteiro com 5000 dígitos, JSON muito aninhado, UTF-8 inválido, chave duplicada. Depois de adaptadas ao contrato real, essas ideias revelaram **mais 6 defeitos** (INT-X06 a X11).
- Conclusão: **prompt genérico explora largura, prompt refinado explora profundidade.** A melhor suíte saiu da combinação dos dois, com curadoria humana no meio.

**P3 – Contrato de API.**
- Mudou o ponto de vista: em vez de "o que a API faz", o prompt pergunta **"do que o front-end depende"**. Isso gerou casos que os outros dois não geraram:
  - simulação fiel do `FormData` (checkbox desmarcado não é enviado);
  - verificação de que `entropy` é número, para virar "N bits" na tela;
  - leitura estrita como `JSON.parse`, que rejeita `NaN`;
  - **meta-testes do próprio validador de schema** (INT-C02/C03), para evitar um validador quebrado deixando tudo verde.
- Nenhum teste falhou, porque o contrato **que o front-end usa hoje** está sendo cumprido.
- A lista de riscos do P3 apontou a falta de `Cache-Control: no-store` numa resposta que contém senha. Isso virou o INT-X10.

## Quais ajustes de prompt foram necessários

| # | Ajuste (v1 → v2) | Efeito observado |
|---|---|---|
| 1 | **Colar o código real** (rota, trechos do serviço, `Config`, `create_app`) em vez de descrever o sistema | Eliminou 100% das invenções de endpoint, campos e limites |
| 2 | Proibir explicitamente: "não invente endpoints, campos ou mensagens" | Os asserts passaram a usar as mensagens literais do código |
| 3 | Proibir mocks das camadas internas | A P2 v1 fazia `monkeypatch` no gerador, o que já não seria teste de integração |
| 4 | **Lista numerada de cobertura mínima**, incluindo pontos de integração (item 7: `create_app` × `Config`) | Levou ao defeito mais grave (INT-E19/E20), que a v1 nem tangenciou |
| 5 | **"Derive o comportamento real do código antes de cada assert"** + convenção `xfail(strict=True)` para defeitos | Mudou o resultado: em vez de testes vermelhos ambíguos, uma tabela "real × esperado × defeito?" e uma suíte verde que documenta os defeitos |
| 6 | Apontar armadilhas da linguagem (`bool` é subclasse de `int`; `[] or {}` vira `{}`) | Direcionou a análise para INT-E04 e INT-E12. *Ressalva:* parte do mérito aqui é de quem escreveu o prompt, que já tinha lido o código |
| 7 | Formato fixo de saída: tabela + arquivo único + IDs (`INT-Fxx`/`Exx`/`Cxx`) + AAA | Rastreabilidade direta entre tabela, código e este catálogo |
| 8 | Pedir **lista de premissas a validar** | A LLM sinalizou o que não sabia (ex.: nomes das chaves de `strength`), em vez de chutar em silêncio |
| 9 | (P3) Dar o código **dos dois lados** e exigir `required` só para o que o consumidor lê | O contrato saiu "do tamanho do consumidor", com leitor tolerante nas respostas |
| 10 | (P3) Proibir bibliotecas externas (`jsonschema`) | A LLM escreveu um validador próprio e, sem ser pedido, os meta-testes dele |

**Ajuste que ficou faltando.** No P3, resumi `evaluate_strength` em um comentário e omiti o `round(..., 2)`. A LLM então afirmou que a entropia "é um float sem arredondamento" (risco nº 9 em [`p3-contrato.md`](docs/saidas-llm/p3-contrato.md)), o que é falso. **Lição: o que o prompt omite, a LLM preenche.** Trecho literal de código é mais seguro que resumo.

**Ajuste feito na curadoria.** A P2 v1 propôs JSON aninhado com 2000 níveis para provocar `RecursionError`, mas o Python 3.12 aceita essa profundidade. O 500 só apareceu com 100 mil níveis (INT-X07). A ideia estava certa, mas o dado de teste precisou de calibração empírica.

## Defeitos encontrados no sistema

Todos foram reproduzidos executando a API. Detalhes e casos em [`docs/casos-de-teste.md`](docs/casos-de-teste.md).

| Severidade | Defeito | Testes |
|---|---|---|
| Alta | `PasswordService` ignora a `Config` passada a `create_app` (limites e padrão) | INT-E19, E20 |
| Alta | Corpo JSON lista/string/número → **500** (`AttributeError`); JSON muito aninhado → **500** (`RecursionError`) | INT-E11, X07 |
| Alta | Flags como string (`"false"`) **ativam** o grupo: o cliente pede sem símbolos e recebe com símbolos | INT-E08 |
| Média | Corpo inválido aceito em silêncio (sintaxe errada, sem Content-Type, UTF-8 inválido, inteiro gigante, falsy não-objeto) → 200 com senha padrão | INT-E12, E13, E14, X06, X08 |
| Média | Resposta com senha sem `Cache-Control: no-store`; sem `MAX_CONTENT_LENGTH` | INT-X10, X11 |
| Baixa | `null` nas flags vira False; `length: true` gera a mensagem errada; campos desconhecidos ignorados; 404/405 em HTML | INT-E09, E04, X09, E17 |

A causa raiz da maior parte deles está em uma linha de `routes.py`: `request.get_json(silent=True) or {}`. Ela troca "não consegui ler o corpo" por "use os padrões".

## Boas práticas que levo para prompts de testes de integração

1. **Contexto literal > descrição.** Cole o código dos dois lados da integração. Resumos geram alucinação.
2. **Peça a análise antes do código.** Pedir a tabela "comportamento real × esperado" fez a LLM raciocinar sobre o código, em vez de escrever asserts de memória.
3. **Defina como registrar defeitos** (ex.: `xfail(strict=True)`). Sem isso, a LLM escreve testes que só falham, e ninguém sabe se o erro é do teste ou do sistema.
4. **Liste explicitamente os pontos de integração.** A LLM não vai procurar sozinha a costura entre `create_app` e `Config`.
5. **Use um prompt genérico como brainstorm**, nunca como suíte. As ideias são boas, o contrato é inventado.
6. **Valide tudo executando.** 1 dos 14 riscos do P3 estava errado e 1 dado da P2 v1 precisou de recalibração. A GenAI é um copiloto, a curadoria continua humana.

## Limitações e cuidados percebidos no uso da IA

1. **Invenção de contrato sem contexto.** As v1 criaram endpoint, campos, funcionalidades (lote, `/health`) e limites plausíveis, porém inexistentes. Mesmo padrão observado no módulo `04-documentacao-discovery`.
2. **Testes "que passam" não provam o motivo.** Um `xfail` estrito confirma que o teste falha, não *por que* falha. Precisei verificar cada comportamento real alegado antes de aceitar a classificação de defeito.
3. **Viés do autor do prompt.** As dicas da v2 sobre armadilhas de Python vieram da minha própria leitura do código. A v2 é melhor também porque eu já sabia onde olhar.
4. **Volume não é qualidade.** O P3 gerou 499 casos parametrizados, todos verdes. A contribuição mais útil dele foi a lista de riscos em prosa, não a contagem de testes.

## Link do repositório

https://github.com/murillostein/especializacao-akcit/tree/main/05-testes-de-integracao-genai

---

## Texto para o fórum

> **Link do projeto:** https://github.com/murillostein/especializacao-akcit/tree/main/05-testes-de-integracao-genai
>
> **Cenário:** integração front-end (`app.js`) → API REST Flask (`POST /api/passwords`) → `PasswordService` → `Config`, no Gerador de Senhas do projeto prático. Todos os testes usam as camadas reais, sem mocks.
>
> **Tipos de prompt:**
> - **P1 – Cenários de integração** (caminho de sucesso entre as camadas)
> - **P2 – Casos de erro e dados de teste** (fronteiras, tipos errados, corpo malformado, configuração)
> - **P3 – Contrato de API orientado ao consumidor** (contrato inferido do JS e do Flask, respostas validadas por JSON Schema)
>
> P1 e P2 foram feitos em duas versões: uma linha genérica (v1) e um prompt refinado (v2). Cada prompt rodou em sessão isolada, e as respostas brutas estão no repositório.
>
> **Como cada prompt influenciou a qualidade e a diversidade:**
> - As **v1** tiveram ótima diversidade (concorrência, `NaN`, JSON aninhado, cabeçalhos de cache), mas inventaram o contrato da API: só **2 de 66** e **0 de 90** testes rodaram contra o sistema real.
> - A **P1 v2** gerou 34 cenários corretos e profundos (recalcula a entropia, cobre as 15 combinações de grupos), mas não encontrou defeitos, o que é esperado para caminho feliz.
> - A **P2 v2** foi a mais valiosa: **8 defeitos reais**, todos confirmados. O mais grave é que a `Config` passada a `create_app` é ignorada pelo serviço. Também há **500** com corpo JSON do tipo lista.
> - O **P3** trouxe o ponto de vista do consumidor (simula o `FormData`, valida tipos que o JS exibe) e apontou a falta de `Cache-Control: no-store` numa resposta que contém senha.
> - A curadoria das ideias das v1, adaptadas ao contrato real, revelou **mais 6 defeitos**.
>
> **Ajustes de prompt que fizeram diferença:**
> 1. colar o código real, em vez de descrevê-lo (acabaram as invenções);
> 2. proibir mocks e invenção de endpoints e mensagens;
> 3. listar os pontos de integração a cobrir (foi isso que levou ao defeito da `Config`);
> 4. exigir "derive o comportamento real do código antes do assert" e marcar defeitos com `xfail(strict=True)`, o que gerou uma suíte verde que documenta 34 defeitos;
> 5. pedir uma lista de premissas a validar.
>
> O que faltou: resumi uma função no P3 e a LLM "completou" errado (disse que a entropia não era arredondada). **Trecho literal de código é melhor que resumo.**
>
> **Conclusão:** prompt genérico serve para explorar largura, prompt refinado para explorar profundidade. A suíte mais robusta veio da combinação dos dois, com validação humana executando cada caso.
