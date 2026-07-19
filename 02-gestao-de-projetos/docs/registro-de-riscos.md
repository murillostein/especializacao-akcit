# Registro de Riscos

**Projeto**: Gerador de Senhas (01-projeto-pratico)
**Data**: 2026-07-19
**Responsavel**: Murillo Stein

---

## Escala de avaliacao

**Probabilidade**

| Nivel | Criterio |
|-------|----------|
| Baixa | Evento improvavel no ciclo de vida do projeto |
| Media | Evento com chance razoavel de ocorrencia |
| Alta | Evento esperado ou ja observado em projetos similares |

**Impacto**

| Nivel | Criterio |
|-------|----------|
| Baixo | Nao afeta entrega ou funcionamento |
| Medio | Afeta qualidade ou prazo de forma controlavel |
| Alto | Compromete seguranca, confiabilidade ou entrega |

**Nivel de risco** (Probabilidade x Impacto)

| | Baixo | Medio | Alto |
|---|-------|-------|------|
| **Baixa** | Baixo | Baixo | Medio |
| **Media** | Baixo | Medio | Alto |
| **Alta** | Medio | Alto | Critico |

---

## Riscos identificados

### R01 - Exposicao da SECRET_KEY em repositorio

| Campo | Valor |
|-------|-------|
| **Categoria** | Seguranca |
| **Descricao** | A SECRET_KEY do Flask pode ser acidentalmente versionada no `.env` se o `.gitignore` nao estiver configurado corretamente |
| **Causa raiz** | Arquivo `.env` nao incluido no `.gitignore`, ou desenvolvedor criando o arquivo com nome diferente |
| **Consequencia** | Comprometimento da integridade das sessoes Flask; possibilidade de forja de cookies |
| **Probabilidade** | Media |
| **Impacto** | Alto |
| **Nivel** | Alto |
| **Gatilho** | Commit com arquivo `.env` listado no `git status` |

---

### R02 - Ausencia de HTTPS em ambiente de producao

| Campo | Valor |
|-------|-------|
| **Categoria** | Seguranca |
| **Descricao** | A aplicacao foi configurada para rodar em HTTP. Em producao, senhas geradas trafegariam em texto claro |
| **Causa raiz** | Ausencia de configuracao de TLS/SSL no servidor de aplicacao ou proxy reverso |
| **Consequencia** | Senhas interceptaveis por ataque man-in-the-middle; perda de confianca do usuario |
| **Probabilidade** | Alta |
| **Impacto** | Alto |
| **Nivel** | Critico |
| **Gatilho** | Deploy em servidor publico sem certificado SSL |

---

### R03 - Sem rate limiting na API de geracao de senhas

| Campo | Valor |
|-------|-------|
| **Categoria** | Seguranca |
| **Descricao** | O endpoint `/generate` nao possui limite de requisicoes por IP ou periodo |
| **Causa raiz** | Ausencia de middleware de throttling (Flask-Limiter ou similar) |
| **Consequencia** | Possibilidade de abuso para enumeracao ou sobrecarga do servidor |
| **Probabilidade** | Media |
| **Impacto** | Medio |
| **Nivel** | Medio |
| **Gatilho** | Pico anormal de requisicoes detectado nos logs |

---

### R04 - Vulnerabilidades em dependencias desatualizadas

| Campo | Valor |
|-------|-------|
| **Categoria** | Tecnico |
| **Descricao** | Dependencias listadas no `requirements.txt` sem versionamento fixo podem introduzir CVEs conhecidos |
| **Causa raiz** | Ausencia de pinagem de versao e de varredura automatica de vulnerabilidades (pip-audit, Dependabot) |
| **Consequencia** | Exploracao de vulnerabilidade conhecida no Flask ou dependencias transitivas |
| **Probabilidade** | Alta |
| **Impacto** | Alto |
| **Nivel** | Critico |
| **Gatilho** | Publicacao de CVE afetando versao instalada |

---

### R05 - Ausencia de monitoramento e alertas

| Campo | Valor |
|-------|-------|
| **Categoria** | Tecnico |
| **Descricao** | Nao ha mecanismo de observabilidade (logs estruturados, metricas, alertas) na aplicacao |
| **Causa raiz** | Foco no desenvolvimento da feature sem considerar operacao |
| **Consequencia** | Falhas silenciosas nao detectadas; dificuldade de diagnostico em incidentes |
| **Probabilidade** | Alta |
| **Impacto** | Medio |
| **Nivel** | Alto |
| **Gatilho** | Erro reportado por usuario antes de ser detectado internamente |

---

### R06 - Escopo mal definido para evolucoes futuras

| Campo | Valor |
|-------|-------|
| **Categoria** | Projeto |
| **Descricao** | O README lista evolucoes sugeridas sem criterios de aceitacao ou priorizacao |
| **Causa raiz** | Ausencia de backlog formal e processo de gestao de mudancas |
| **Consequencia** | Retrabalho, features incompletas ou conflito de prioridades |
| **Probabilidade** | Baixa |
| **Impacto** | Medio |
| **Nivel** | Baixo |
| **Gatilho** | Solicitacao de nova feature sem especificacao clara |

---

### R07 - Ausencia de processo de resposta a incidentes

| Campo | Valor |
|-------|-------|
| **Categoria** | Operacional |
| **Descricao** | Nao ha runbook ou procedimento documentado para incidentes de seguranca ou disponibilidade |
| **Causa raiz** | Projeto academico sem consideracao de operacao em producao |
| **Consequencia** | Tempo de recuperacao elevado; decisoes incorretas sob pressao |
| **Probabilidade** | Media |
| **Impacto** | Alto |
| **Nivel** | Alto |
| **Gatilho** | Incidente de seguranca ou indisponibilidade da aplicacao |

---

## Mapa de calor

```
                    IMPACTO
                 Baixo | Medio | Alto
               +-------+-------+------+
  Alta         |       |  R05  | R02  |
               |       |       | R04  |
  PROB. Media  |       |  R03  | R01  |
               |       |       | R07  |
  Baixa        |       |  R06  |      |
               +-------+-------+------+
```

Riscos criticos (Alta probabilidade x Alto impacto): **R02, R04**
