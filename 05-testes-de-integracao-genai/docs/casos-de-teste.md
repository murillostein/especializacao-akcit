# Catálogo de casos de teste de integração

Casos registrados na suíte final (`tests/`), com a origem de cada um e o resultado da execução contra o código real de `01-projeto-pratico`.

**Legenda de status**
- **passa**: o comportamento atual está correto.
- **xfail**: defeito confirmado. O teste afirma o comportamento desejado e está marcado com `xfail(strict=True)`, então vai acusar quando o defeito for corrigido.

Contagem por arquivo (pytest 8.3.5, Python 3.12):

| Arquivo | Origem | IDs | Casos executados | Passam | xfail (defeitos) |
|---|---|---|---|---|---|
| `test_integracao_fluxos.py` | P1 v2 | INT-F01 a F08 | 34 | 34 | 0 |
| `test_integracao_erros.py` | P2 v2 | INT-E01 a E20 | 64 | 36 | 28 |
| `test_contrato_api.py` | P3 | INT-C01 a C10 | 499 | 499 | 0 |
| `test_integracao_complementares.py` | Curadoria das saídas v1 | INT-X01 a X11 | 14 | 8 | 6 |
| **Total** | | | **611** | **577** | **34** |

A contagem do P3 é alta porque ele cruza 6 comprimentos com as 16 combinações de checkboxes, em vários testes parametrizados.

---

## P1 v2 – Cenários de integração (caminho de sucesso)

| ID | Cenário | Status |
|---|---|---|
| INT-F01 | Cada grupo de caracteres isolado e todos combinados geram senha só com caracteres permitidos | passa |
| INT-F02 | `length` omitido, `null`, ausente com flags explícitas ou sem corpo JSON → comprimento padrão vindo de `Config` | passa |
| INT-F03 | Limites exatos de `Config` (8 e 64) são aceitos | passa |
| INT-F04 | `strength` (entropia, rótulo, score) bate com o recálculo feito no teste a partir da senha devolvida, uma faixa por nível | passa |
| INT-F05 | As 15 combinações de grupos, 30 vezes cada: todo grupo selecionado aparece e nenhum outro aparece | passa |
| INT-F06 | 50 chamadas consecutivas → 50 senhas distintas | passa |
| INT-F07 | Parâmetros de uma requisição não vazam para a seguinte | passa |
| INT-F08 | `/` e a API são servidas pela mesma aplicação | passa |

## P2 v2 – Casos de erro e dados de fronteira

| ID | Cenário | Status |
|---|---|---|
| INT-E01 | Fronteiras válidas de `length` (mín., máx., `null`, ausente) | passa |
| INT-E02 | `length` abaixo do mínimo, zero, negativo, acima do máximo, 10^30 → 400 com a mensagem certa | passa |
| INT-E03 | `length` como string, float, lista ou objeto → 400 "deve ser um inteiro" | passa |
| INT-E04 | `length: true/false` responde com a mensagem de **mínimo** (bool é subclasse de int) | **xfail** |
| INT-E05 | Nenhum grupo selecionado → 400 | passa |
| INT-E06 | Ordem de validação: o comprimento é validado antes dos grupos | passa |
| INT-E07 | Flags falsy de outro tipo (`0`, `""`, `[]`, `{}`) → 400 | passa |
| INT-E08 | Flags `"false"`/`"0"` (strings) **ativam** o grupo e retornam 200 | **xfail** |
| INT-E09 | Flags `null` viram False, enquanto `length: null` usa o padrão | **xfail** |
| INT-E10 | Corpo ausente ou `{}` → senha com valores padrão | passa |
| INT-E11 | Corpo JSON lista/string/número (`[8]`, `"abc"`, `42`) → **500** (`AttributeError`) | **xfail** |
| INT-E12 | Corpo JSON falsy não-objeto (`[]`, `0`, `null`...) → aceito com padrões | **xfail** |
| INT-E13 | JSON com erro de sintaxe → 200 com padrões (`silent=True` engole o erro) | **xfail** |
| INT-E14 | Corpo sem Content-Type JSON é ignorado; `length: 7` escapa da validação | **xfail** |
| INT-E15 | GET/PUT/PATCH/DELETE → 405 com `Allow: POST` | passa |
| INT-E16 | Rotas parecidas (`/api/password`, barra final...) → 404 | passa |
| INT-E17 | 404/405 da API são devolvidos em HTML, não em JSON | **xfail** |
| INT-E18 | `create_app(config_class=...)` carrega a subclasse em `app.config` | passa |
| INT-E19 | Limites MIN/MAX da Config passada a `create_app` são **ignorados** pelo serviço | **xfail** |
| INT-E20 | `DEFAULT_PASSWORD_LENGTH` da Config passada a `create_app` é ignorado | **xfail** |

## P3 – Contrato de API (front-end ↔ back-end)

| ID | Cenário | Status |
|---|---|---|
| INT-C01 | Todo payload que o `app.js` consegue montar é válido no schema de requisição | passa |
| INT-C02 | Meta-teste: o validador próprio detecta 22 violações conhecidas | passa |
| INT-C03 | Meta-teste: o validador aceita variações toleradas (campos extras, `score` ausente) | passa |
| INT-C04 | Resposta 200 válida no schema para 90 payloads reais do consumidor | passa |
| INT-C05 | Cada campo lido pelo JS existe e tem o tipo esperado (`entropy` numérico → "N bits") | passa |
| INT-C06 | Resposta 200 com `Content-Type: application/json` | passa |
| INT-C07 | Senha respeita o slider e os checkboxes desmarcados | passa |
| INT-C08 | Todos os checkboxes desmarcados → 400 válido no schema de erro | passa |
| INT-C09 | No erro, `data.error` é string não vazia (sem cair no fallback genérico da UI) | passa |
| INT-C10 | Resposta 400 também em JSON | passa |

## Curadoria das saídas v1 – casos complementares

Ideias que só apareceram nas respostas aos prompts genéricos. Cada uma foi reescrita para o contrato real e confirmada executando a API.

| ID | Cenário | Origem | Status |
|---|---|---|---|
| INT-X01 | `NaN`/`Infinity` em `length` → 400 | P2 v1 | passa |
| INT-X02 | Chave JSON duplicada: vale o último valor, que é validado | P2 v1 | passa |
| INT-X03 | Mensagem de erro não reflete a entrada nem expõe traceback | P1 v1, P2 v1 | passa |
| INT-X04 | A API continua funcional depois de uma sequência de erros (inclusive um 500) | P2 v1 | passa |
| INT-X05 | 50 requisições concorrentes → 50 senhas distintas | P1 v1 | passa |
| INT-X06 | Inteiro com 5000 dígitos é ignorado em silêncio (200 com padrão) | P2 v1 | **xfail** |
| INT-X07 | JSON com 100 mil níveis de aninhamento → 500 (`RecursionError`) | P2 v1 (ajustado) | **xfail** |
| INT-X08 | Corpo com UTF-8 inválido é aceito com padrões | P2 v1 | **xfail** |
| INT-X09 | Campo com erro de digitação (`lenght: 7`) é ignorado, sem validação | P2 v1 | **xfail** |
| INT-X10 | Resposta com senha sem `Cache-Control: no-store` | P1 v1, P3 | **xfail** |
| INT-X11 | Sem `MAX_CONTENT_LENGTH`: corpo de 1 MB é processado | P1 v1, P2 v1 | **xfail** |
