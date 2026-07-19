# Estrategias de Resposta aos Riscos

**Projeto**: Gerador de Senhas (01-projeto-pratico)
**Data**: 2026-07-19

---

## Estrategias adotadas

As quatro estrategias classicas de resposta a riscos negativos foram consideradas:

- **Mitigar**: reduzir a probabilidade ou o impacto
- **Evitar**: eliminar a causa ou proteger o objetivo do risco
- **Transferir**: mover a responsabilidade para terceiros
- **Aceitar**: reconhecer o risco sem acao imediata (passiva) ou com plano de contingencia (ativa)

---

## R01 - Exposicao da SECRET_KEY

**Estrategia**: Evitar

**Acoes**:
1. Garantir que `.env` esta listado no `.gitignore` (ja presente no projeto).
2. Adicionar `.env.local` e `.env.*.local` ao `.gitignore` como medida de redundancia.
3. Configurar `git-secrets` ou `pre-commit` com hook que rejeita commits contendo padroes de chave.
4. Documentar no `README.md` que a SECRET_KEY deve ser rotacionada antes de qualquer deploy.

**Responsavel**: desenvolvedor responsavel pelo deploy
**Prazo**: antes do primeiro deploy em servidor publico
**Indicador de eficacia**: zero commits com `.env` nos ultimos 90 dias de historico

---

## R02 - Ausencia de HTTPS em producao

**Estrategia**: Evitar

**Acoes**:
1. Configurar proxy reverso (Nginx ou Caddy) com certificado SSL/TLS automatico via Let's Encrypt.
2. Adicionar redirecionamento forcado de HTTP para HTTPS.
3. Habilitar o header `Strict-Transport-Security` (HSTS) na configuracao do Flask ou do proxy.
4. Incluir checklist de seguranca pre-deploy no repositorio.

**Responsavel**: responsavel pela infraestrutura
**Prazo**: obrigatorio antes de qualquer exposicao publica
**Indicador de eficacia**: resultado A+ no SSL Labs em teste pos-deploy

---

## R03 - Sem rate limiting na API

**Estrategia**: Mitigar

**Acoes**:
1. Instalar e configurar `Flask-Limiter` com limite de 20 requisicoes por minuto por IP.
2. Retornar HTTP 429 com mensagem clara ao atingir o limite.
3. Registrar tentativas bloqueadas em log estruturado para analise posterior.

**Responsavel**: desenvolvedor backend
**Prazo**: sprint apos o deploy inicial
**Indicador de eficacia**: sem abuso detectado nos logs por 30 dias pos-implantacao

**Exemplo de configuracao**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, default_limits=["20 per minute"])
```

---

## R04 - Vulnerabilidades em dependencias (PRIORITARIO)

**Estrategia**: Mitigar

Esta estrategia foi considerada a mais importante por ser de alta probabilidade, alto impacto e facilmente automatizavel.

**Acoes**:
1. Fixar versoes no `requirements.txt` usando `pip freeze > requirements.txt` apos ambiente estavel.
2. Habilitar o **GitHub Dependabot** para varredura automatica de dependencias Python.
3. Integrar `pip-audit` no pipeline de CI para bloquear merges com CVEs conhecidos.
4. Revisar dependencias a cada release ou a cada 30 dias, o que ocorrer primeiro.

**Responsavel**: desenvolvedor; revisao no code review
**Prazo**: imediato (antes do proximo push para main)
**Indicador de eficacia**: zero CVEs com severidade alta ou critica nas dependencias instaladas

**Comando de varredura manual**:
```bash
pip install pip-audit
pip-audit
```

**Por que esta estrategia e prioritaria**:
A geracao segura de senhas depende diretamente da integridade do stack. Uma vulnerabilidade no Flask ou em uma dependencia transitiva pode comprometer todo o proposito do projeto, mesmo que o modulo `secrets` esteja sendo usado corretamente. A automacao torna o custo de manutencao quase nulo.

---

## R05 - Ausencia de monitoramento

**Estrategia**: Mitigar

**Acoes**:
1. Substituir `print` por `logging` com nivel e formato padrao (JSON em producao).
2. Configurar rotacao de logs com `RotatingFileHandler`.
3. Para producao: integrar com servico externo (ex: Logtail, Papertrail, ou CloudWatch).
4. Criar alerta basico via e-mail ou webhook para erros com nivel `ERROR` ou superior.

**Responsavel**: desenvolvedor
**Prazo**: antes do deploy em producao
**Indicador de eficacia**: 100% dos erros HTTP 5xx registrados em log com rastreamento

---

## R06 - Escopo mal definido

**Estrategia**: Aceitar (ativa)

Por se tratar de projeto academico com escopo controlado, o risco e aceito com o seguinte plano de contingencia:

**Plano de contingencia**:
- Antes de implementar qualquer evolucao listada no README, abrir uma issue no GitHub com criterios de aceitacao.
- Revisar o backlog a cada entrega de modulo da especializacao.

**Responsavel**: responsavel pelo projeto
**Prazo**: continuo

---

## R07 - Ausencia de processo de resposta a incidentes

**Estrategia**: Mitigar

**Acoes**:
1. Criar `docs/runbook.md` com passos para os cenarios de incidente mais provaveis (indisponibilidade, brecha de seguranca).
2. Definir canal de comunicacao de incidentes (e-mail ou grupo de mensagens).
3. Estabelecer SLA informal de resposta: 4h para incidentes criticos.

**Responsavel**: responsavel pelo projeto
**Prazo**: antes do deploy em producao

---

## Sumario executivo de acoes

| ID | Estrategia | Acao principal | Prazo | Prioridade |
|----|------------|----------------|-------|------------|
| R01 | Evitar | Hook pre-commit + gitignore auditado | Pre-deploy | Alta |
| R02 | Evitar | HTTPS via Nginx + Let's Encrypt | Pre-deploy | Critica |
| R03 | Mitigar | Flask-Limiter com 20 req/min | Pos-deploy | Media |
| R04 | Mitigar | pip-audit + Dependabot + pinagem | Imediato | Critica |
| R05 | Mitigar | Logging estruturado + alertas | Pre-deploy | Alta |
| R06 | Aceitar | Issue no GitHub antes de qualquer evolucao | Continuo | Baixa |
| R07 | Mitigar | Runbook de incidentes | Pre-deploy | Alta |
