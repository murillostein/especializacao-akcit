# DevOps com IA Generativa - Diagnóstico de Falhas no Pipeline

## Contexto

Este módulo aplica a Unidade 5 (Projeto Integrador de DevOps com IA Generativa) ao mesmo tema dos módulos anteriores, o Gerador de Senhas. A proposta do laboratório é ter uma aplicação Python com um **erro intencional**, testes automatizados, um pipeline de CI/CD e um **agente de IA generativa** que lê o log da falha e sugere a correção.

A aplicação é um **estimador de tempo de quebra de senha**: recebe a entropia calculada pelo `PasswordService.evaluate_strength` do módulo `01-projeto-pratico` e diz quanto tempo, em média, um atacante levaria para achar a senha por força bruta, e se isso atende a política de segurança.

## Fluxo do pipeline

```mermaid
flowchart LR
    A[push / MR / PR] --> B[Job testes<br/>pytest -v + junit]
    B -- passou --> C[Pipeline verde]
    B -- falhou --> D[Job diagnostico-ia]
    D --> E[Agente recorta o log,<br/>anexa o código citado,<br/>mascara segredos]
    E --> F[Claude API<br/>claude-opus-5-5]
    F --> G[diagnostico.md<br/>artefato + resumo do job<br/>+ comentário no MR/PR]
    G --> H{Revisão humana}
    H -- valida e corrige --> A
```

O job de diagnóstico **nunca altera código nem muda o status do pipeline**. Quem reprova a entrega é o job de testes. A IA só produz uma sugestão, que um humano valida.

## Estrutura

```text
06-devops-genai/
|-- README.md                       (este arquivo: análise e texto do fórum)
|-- .gitlab-ci.yml                  (pipeline GitLab CI)
|-- requirements.txt                (pytest)
|-- requirements-agente.txt         (anthropic, só no job de diagnóstico)
|-- pytest.ini
|-- app/
|   |-- config.py                   (política lida do ambiente; o erro intencional está no commit 96cbd33)
|   |-- tempo_quebra.py             (estimativa, formatação, avaliação)
|   `-- __main__.py                 (python -m app <bits>)
|-- agente/
|   `-- diagnosticar_falha.py       (agente de diagnóstico com GenAI)
|-- tests/
|   |-- test_tempo_quebra.py        (28 testes da aplicação: 16 originais + 12 da validação humana)
|   `-- test_agente.py              (8 testes das partes determinísticas do agente)
`-- docs/
    |-- evidencias/                 (logs do pytest, prompts enviados, relatório sem credencial)
    |-- saida-ia/                   (respostas brutas da LLM, sem edição)
    `-- correcao/
        `-- correcao-validada.patch (correção depois da validação humana, já aplicada)

.github/workflows/devops-genai.yml  (pipeline GitHub Actions, na raiz do repositório por exigência do GitHub)
```

## O erro intencional

Na versão original (commit `96cbd33`), em `app/config.py`, a taxa de tentativas do atacante era lida do ambiente **sem conversão de tipo**:

```python
"tentativas_por_segundo": os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"),   # str, não float
"tempo_minimo_anos": float(os.getenv("TEMPO_MINIMO_ANOS", "100")),       # este está certo
```

`os.getenv` sempre devolve `str`. O erro **nasce** na configuração, mas só **estoura** longe dali, em `app/tempo_quebra.py:31`, quando um `float` é dividido pela string `'1e10'`. Escolhi esse cenário de propósito: o traceback aponta para o lugar errado, e `config.py` nem aparece nele. Isso testa se a IA encontra a causa raiz ou só remenda o sintoma.

Resultado no pipeline: **5 testes falham** (2 `AssertionError` no contrato da configuração e 3 `TypeError` na estimativa). Os testes que passam a taxa explicitamente continuam passando. Log completo em [`docs/evidencias/pytest-falha.log`](docs/evidencias/pytest-falha.log).

## Execução no pipeline (GitHub Actions)

O módulo foi entregue no [PR #1](https://github.com/murillostein/especializacao-akcit/pull/1), em dois commits:

| Commit | O que mudou | Execução | Resultado |
|---|---|---|---|
| `96cbd33` | Módulo com o erro intencional | [push](https://github.com/murillostein/especializacao-akcit/actions/runs/43480531653) e [pull_request](https://github.com/murillostein/especializacao-akcit/actions/runs/43481372571) | ❌ testes: `5 failed, 19 passed`. ✅ job de diagnóstico rodou, gerou o prompt e o relatório |
| 2º commit | Correção validada + 12 testes | ver PR #1 | ✅ `36 passed`. O job de diagnóstico é pulado |

No CI, o job de diagnóstico rodou **sem o secret `ANTHROPIC_API_KEY`**. Como previsto no desenho do agente, ele não quebrou: salvou o prompt completo (13.198 caracteres) como artefato e registrou "sem credencial da API" no relatório. A análise da IA registrada neste módulo foi feita com esse mesmo prompt, no mesmo modelo, em sessão isolada (ver o experimento abaixo). Com o secret configurado, o mesmo job publica o diagnóstico no resumo da execução e como comentário no PR.

## Como executar

**Localmente**

```bash
cd 06-devops-genai
pip install -r requirements.txt -r requirements-agente.txt
python -m pytest -v                                           # versão atual: 36 passed

# Reproduzir a falha do laboratório
git checkout 96cbd33 -- app/config.py tests/test_tempo_quebra.py
python -m pytest -v 2>&1 | tee pytest.log                     # 5 failed, 19 passed
python agente/diagnosticar_falha.py --log pytest.log          # gera diagnostico.md e prompt-enviado.md
git checkout HEAD -- app/config.py tests/test_tempo_quebra.py # volta para a versão corrigida
```

Sem `ANTHROPIC_API_KEY`, o agente não quebra: salva o prompt completo e um relatório dizendo que a análise não foi executada ([exemplo](docs/evidencias/diagnostico-sem-credencial.md)). A opção `--somente-prompt` faz o mesmo de propósito.

**GitHub Actions**: o workflow `.github/workflows/devops-genai.yml` roda em push e PR que toquem `06-devops-genai/`. Crie o secret `ANTHROPIC_API_KEY` no repositório. Em PR, o diagnóstico vira comentário; em qualquer execução, aparece no resumo do job e como artefato `diagnostico-ia`.

**GitLab CI**: em *Settings > CI/CD > General pipelines*, aponte o arquivo de configuração para `06-devops-genai/.gitlab-ci.yml`. Crie as variáveis mascaradas `ANTHROPIC_API_KEY` e, para comentar no Merge Request, `GITLAB_API_TOKEN` (escopo `api`). O job `diagnostico_ia` usa `when: on_failure` e `allow_failure: true`.

**Correção validada:** já aplicada no segundo commit. O arquivo [`correcao-validada.patch`](docs/correcao/correcao-validada.patch) fica como registro do que mudou em relação à versão com erro.

## O agente de diagnóstico

[`agente/diagnosticar_falha.py`](agente/diagnosticar_falha.py) faz uma única chamada à API do Claude (`claude-opus-5-5`). Antes disso, prepara o contexto:

| Etapa | Por quê |
|---|---|
| Recorta o log a partir de `FAILURES` (limite de 40 mil caracteres, com aviso explícito se cortar) | O cabeçalho do pytest não ajuda e só gasta tokens |
| Anexa, numerado, o **código-fonte citado no traceback** | Lição do módulo 05: contexto literal evita que a LLM invente código |
| Anexa também os **módulos do projeto importados** por esses arquivos | O traceback mostra onde o erro estoura, não onde nasce (ver experimento abaixo) |
| Mascara segredos (`sk-ant-`, `glpat-`, `ghp_`, `AKIA...`, `token=...`) | O log vai para um serviço externo |
| Troca caminhos absolutos da máquina por `<projeto>` e `<home>` | Na primeira execução local, o log continha o caminho com o meu nome de usuário |
| System prompt com regras: não inventar, separar fato de hipótese, buscar causa raiz, **não relaxar testes** | Evita a "correção" que só silencia o teste |
| Formato fixo: resumo, evidências, causa raiz, diff, como validar, confiança e premissas, prevenção | Torna a resposta revisável e comparável entre execuções |
| Salva o prompt enviado (`prompt-enviado.md`) como artefato | Auditoria: dá para ver exatamente o que a IA recebeu |
| Trata erros da API (credencial, 429, 5xx, rede, recusa) e sempre sai com código 0 | Uma falha na IA não pode esconder nem substituir a falha dos testes |
| Usa `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) | Se o modelo recusar o pedido, a própria API refaz a chamada num modelo alternativo |

## Experimento: quanto contexto a IA precisa?

Rodei o mesmo log com dois prompts gerados pelo agente:

- **A**: só os arquivos do traceback (`--sem-imports`): `tests/test_tempo_quebra.py` e `app/tempo_quebra.py`.
- **B**: o padrão do agente, que inclui também `app/config.py`, importado por `tempo_quebra.py`.

Como não havia chave de API na máquina local, cada prompt foi executado no **mesmo modelo que o agente usa (Claude Opus 5.5)**, em sessão isolada via Claude Code: sem histórico, sem acesso ao repositório, só com o texto do prompt. Os prompts estão em [`docs/evidencias/`](docs/evidencias/) e as respostas brutas em [`docs/saida-ia/`](docs/saida-ia/). No pipeline, o mesmo prompt vai direto para a API.

| | A: só traceback | B: com imports |
|---|---|---|
| Achou que a causa está em `config.py`? | **Sim**, por dedução: o assert `isinstance('1e10', float)` entrega | **Sim**, apontando `config.py:14` |
| Diff aplicável? | **Não**: esboço com linhas supostas (`tentativas = ...`), avisado como esboço | **Sim**: uma linha, aplica direto |
| Rejeitou a correção só no sintoma (`float()` em `tempo_quebra.py`)? | Sim, explicando que os testes de contrato continuariam falhando | Sim |
| Defendeu não relaxar os testes? | Sim | Sim |
| Afirmações erradas | **1 hipótese falsa**: que `tempo_minimo_anos` teria o mesmo defeito (a linha 15 já converte). Estava marcada como hipótese | Nenhuma encontrada. A conta "11 que passaram = 4 com taxa explícita + 7 parametrizados" confere |
| Confiança declarada | Alta no diagnóstico, média na correção | Alta |

**Leitura:** com pouco contexto, a IA acertou a direção, mas preencheu as lacunas com suposições: inventou as linhas do diff e "estendeu" o defeito para um campo sadio. Com o arquivo certo no prompt, a resposta virou um patch exato. A qualidade do diagnóstico dependeu mais do **contexto que o agente monta** do que do modelo.

## Validação humana da correção sugerida

Apliquei a correção da IA (prompt B) numa cópia do módulo: **24/24 testes passaram**, e o pipeline ficaria verde. Mesmo assim, testei à mão os valores que a variável de ambiente pode receber:

| `TENTATIVAS_POR_SEGUNDO` | Com a correção da IA | Problema |
|---|---|---|
| `abc` | `ValueError: could not convert string to float` | Aceitável, mas a mensagem não diz qual variável |
| `0` | `ZeroDivisionError` | Erro tardio, no meio do cálculo |
| `-5` | "instantâneo" | **Silencioso**: resultado sem sentido, sem erro |
| `inf` | "instantâneo" | **Silencioso** |
| `nan` | "mais de mil anos" e "**NÃO** atende a política" | **Contraditório**: a interface diria as duas coisas ao mesmo tempo |

Nenhum teste cobria esses casos, então "pipeline verde" não significava "correção completa". O prompt A chegou a sugerir validar `> 0`. O B, mais preciso no patch, não sugeriu.

A [correção validada](docs/correcao/correcao-validada.patch) mantém a ideia da IA (converter na fronteira, em `config.py`), mas:

1. centraliza a leitura num helper `_ler_float_positivo(nome, padrao)`, que é a medida de prevenção nº 1 sugerida pelas duas respostas;
2. rejeita valores não numéricos, zero, negativos, `inf` e `nan` com `ValueError` que **cita a variável**;
3. aplica a mesma regra a `TEMPO_MINIMO_ANOS`;
4. adiciona 12 casos de teste (`test_politica_rejeita_valores_invalidos`) com os valores acima.

Resultado: **36 passed** ([log](docs/evidencias/pytest-apos-correcao.log)).

> Observação: o experimento A/B rodou quando a suíte tinha só os 16 testes da aplicação (`5 failed, 11 passed`). Os 8 testes do agente vieram depois. Por isso, no pipeline, a falha aparece como `5 failed, 19 passed`.

## Desafios encontrados

1. **A causa raiz não aparece no log.** `config.py` não está em nenhuma linha do traceback. A primeira versão do agente só anexava os arquivos citados, e foi isso que motivou a inclusão dos módulos importados.
2. **Vazamento de dados no log.** O log local tinha o caminho absoluto com o meu nome de usuário. Num runner é `/builds/...`, mas o agente também roda localmente. Adicionei anonimização de caminhos e máscara de segredos antes do envio.
3. **O próprio código "entregava" a resposta.** A primeira versão de `config.py` tinha um comentário "ERRO INTENCIONAL". Com ele no prompt, o teste da IA perderia o sentido. Removi o comentário (o erro fica documentado só aqui).
4. **Falha sem credencial.** Sem `ANTHROPIC_API_KEY`, o SDK não falha ao criar o cliente, só na hora da requisição, com um `TypeError` genérico. Na primeira execução local, o job de diagnóstico quebrou. Passei a checar a credencial antes e a gerar um relatório explicando o motivo.
5. **`tee` esconde a falha.** `pytest | tee pytest.log` devolve o código de saída do `tee` (0), e o pipeline ficaria verde com testes falhando. Os dois pipelines usam `set -o pipefail`.
6. **Pipeline por módulo num repositório com vários módulos.** O GitHub exige o workflow na raiz (`.github/workflows/`), então usei filtro `paths`. No GitLab, mantive o `.gitlab-ci.yml` dentro do módulo e documentei o caminho customizado.
7. **Versão do SDK.** A versão mais nova do pacote `anthropic` tinha saído havia três dias. Fixei a `2.3.0` (com três semanas) depois de confirmar que ela já suportava os parâmetros usados.
8. **Sem chave de API.** Nem a máquina local nem o repositório tinham `ANTHROPIC_API_KEY`. A análise registrada foi feita com o mesmo modelo, em sessão isolada, com exatamente o prompt que o agente gera. A chamada real à API foi verificada até a autenticação (uma chave inválida devolveu `AuthenticationError`, tratado sem derrubar o job). No GitHub Actions, o job de diagnóstico rodou sem a chave e terminou com sucesso, deixando o prompt como artefato.
9. **Avisos do runner.** O GitHub avisou que as actions `checkout@v4`, `setup-python@v5` e `upload/download-artifact@v4` usam Node.js 20, que está sendo descontinuado. Por enquanto, não afeta a execução.

## Reflexão crítica

**Vantagens observadas**

- **Velocidade de triagem.** Em segundos, a IA cruzou 5 falhas de 2 tipos diferentes e concluiu que tinham uma causa só.
- **Raciocínio sobre causa x sintoma.** As duas respostas recusaram o `float()` no lugar do erro e explicaram por quê, citando os testes de contrato.
- **Formato revisável.** Separar evidência, hipótese e confiança deixou fácil conferir cada afirmação.
- **Prevenção útil.** As medidas sugeridas (helper de leitura, `mypy`/`TypedDict`, testes de contrato) são concretas e foram aproveitadas.

**Limitações observadas**

- **Sem contexto, a IA completa o que falta.** O prompt A produziu um diff com linhas inventadas e uma hipótese falsa. As duas vinham sinalizadas, mas um leitor apressado poderia aplicá-las.
- **"Verde" não é "correto".** A correção mais precisa passou em todos os testes e ainda deixava `0`, `-5`, `inf` e `nan` produzirem resultados errados ou contraditórios. A IA otimiza para o que o log mostra, e o log só mostra o que os testes cobrem.
- **Custo e dependência externa.** Cada falha gera uma chamada paga a um serviço externo, que pode falhar, sofrer rate limit ou estar sem crédito. Por isso o agente não pode ser bloqueante.
- **Superfície de vazamento.** Log e código saem do ambiente. Mascarar segredos é obrigatório, e mesmo assim depende de padrões conhecidos.

**Por que validar antes de aplicar.** O diagnóstico da IA é uma hipótese bem escrita, não uma prova. Neste laboratório, validar significou: (1) conferir no código cada afirmação (uma era falsa); (2) aplicar o patch numa cópia e rodar a suíte; (3) testar entradas que a suíte não cobria, o que revelou três comportamentos errados; (4) transformar esses casos em testes, para que a próxima regressão apareça no pipeline e não em produção. A IA acelerou a investigação. A responsabilidade pela correção continuou humana.

## Link do repositório

https://github.com/murillostein/especializacao-akcit/tree/main/06-devops-genai

---

## Texto para o fórum

Texto pronto para colar no fórum do curso:

```text
Olá, pessoal!

1. Repositório

Projeto: https://github.com/murillostein/especializacao-akcit/tree/main/06-devops-genai
Pull Request com o pipeline falhando e depois corrigido: https://github.com/murillostein/especializacao-akcit/pull/1

O repositório está no GitHub, mas o módulo também traz o .gitlab-ci.yml equivalente para o GitLab CI (mesmas etapas, com comentário no Merge Request).

2. Execução do projeto

Mantive o tema do projeto prático da especialização (Gerador de Senhas). A aplicação Python estima o tempo médio para quebrar uma senha por força bruta a partir da entropia e diz se ela atende à política de segurança.

O pipeline (GitHub Actions) tem dois jobs:
- Testes automatizados: checkout, Python 3.12, instalação do requirements.txt e pytest -v com relatório JUnit; o log fica salvo como artefato. Usei "set -o pipefail", porque "pytest | tee" devolveria o código de saída do tee e o pipeline ficaria verde mesmo com testes falhando.
- Diagnóstico com IA generativa: só roda quando o job de testes falha. Um agente em Python lê o log, recorta a seção de falhas, anexa o código citado no traceback e os módulos que ele importa, mascara segredos e envia tudo ao Claude, pedindo a resposta em seções fixas (resumo, evidências, causa raiz, diff, como validar, confiança e premissas, prevenção). Com a chave da API configurada, o resultado vai para o resumo da execução e vira comentário no PR. O agente nunca altera código nem muda o status do pipeline.

Erro intencional: em config.py, a taxa de tentativas do atacante era lida com os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"), sem conversão para float. No pipeline: 5 failed, 19 passed. Trecho do log:

E       AssertionError: assert '1000' == 1000.0
>       return (combinacoes / 2) / tentativas_por_segundo
E       TypeError: unsupported operand type(s) for /: 'float' and 'str'
app/tempo_quebra.py:31: TypeError

Depois da correção, o mesmo pipeline ficou verde (36 passed) e o job de diagnóstico foi pulado.

3. Análise com IA generativa

Escolhi o erro de propósito: ele estoura em tempo_quebra.py, mas nasce em config.py, arquivo que nem aparece no traceback. Queria ver se a IA encontraria a causa raiz ou só remendaria o sintoma.

Rodei o mesmo log com dois prompts gerados pelo agente:
- Só com os arquivos do traceback: a IA deduziu corretamente que o problema estava na configuração, mas o diff sugerido foi um esboço com linhas inventadas, e ela levantou uma hipótese falsa (de que outro campo tinha o mesmo defeito).
- Com os módulos importados (padrão do agente): apontou exatamente config.py, linha 14, e propôs um patch de uma linha: float(os.getenv(...)).

Nos dois casos, a IA recusou a correção "fácil" (converter para float na linha da divisão), explicando que ela trataria só o sintoma e que os testes da configuração continuariam falhando. Também defendeu não relaxar os testes.

Validação humana: apliquei o patch da IA numa cópia, e todos os testes passaram. Mesmo assim, testei à mão outros valores da variável de ambiente: "0" gerava ZeroDivisionError, "-5" e "inf" diziam que a senha seria quebrada "instantaneamente", e "nan" dizia "mais de mil anos" e "NÃO atende a política" ao mesmo tempo. A correção final mantém a ideia da IA (converter na fronteira, em config.py), mas centraliza a leitura numa função que rejeita valores não numéricos, zero, negativos, infinito e NaN com uma mensagem que cita a variável. Também adicionei 12 testes para esses casos.

4. Desafios encontrados

- A causa raiz não aparece no log: a primeira versão do agente só mandava os arquivos do traceback, e foi preciso incluir os módulos importados.
- Dados sensíveis: o log local continha o caminho da minha pasta de usuário. Adicionei anonimização de caminhos e máscara de tokens e chaves antes de enviar qualquer coisa à API.
- Credencial da API: sem chave, o SDK só falha no momento da requisição, e na primeira execução local o agente quebrou. Ele passou a verificar a credencial antes e a gerar um relatório explicando o motivo. No GitHub Actions, o job rodou sem o secret ANTHROPIC_API_KEY: terminou com sucesso e deixou o prompt completo como artefato. A análise registrada foi feita com exatamente esse prompt, no mesmo modelo (Claude Opus 5.5), em sessão isolada.
- Repositório com vários módulos: o GitHub exige o workflow na raiz do repositório, então filtrei a execução por caminho; no GitLab, o arquivo fica dentro do módulo e é preciso configurar o caminho em Settings > CI/CD.
- O próprio código "entregava" a resposta: a primeira versão tinha um comentário "ERRO INTENCIONAL", que removi para o teste da IA ser justo.

5. Reflexão crítica

Vantagens: a IA fez em segundos a triagem de 5 falhas de 2 tipos diferentes e concluiu que tinham uma única causa; separou causa de sintoma e justificou; e o formato com evidências, hipóteses e nível de confiança deixou cada afirmação fácil de conferir. As medidas de prevenção sugeridas (função de leitura centralizada, checagem de tipos com mypy, testes de contrato) foram aproveitadas.

Limitações: sem contexto, a IA preenche lacunas com suposições plausíveis, como linhas de código inventadas e uma hipótese falsa. E "pipeline verde" não significou "correção completa": o patch mais preciso passava em todos os testes e ainda deixava valores inválidos produzirem resultados errados, porque a IA só enxerga o que os testes cobrem. Há ainda o custo, a dependência de um serviço externo e o risco de vazar dados do log.

Por isso é importante validar antes de aplicar: o diagnóstico é uma hipótese bem escrita, não uma prova. Neste laboratório, validar significou conferir cada afirmação no código (uma era falsa), aplicar o patch numa cópia, testar entradas que a suíte não cobria e transformar os problemas encontrados em testes. A IA acelerou a investigação; a responsabilidade pela correção continuou sendo humana.
```
