"""Agente de diagnostico de falhas de CI com IA generativa (Claude).

Le o log do pytest, recorta a secao de falhas, anexa o codigo-fonte citado no
traceback, remove segredos e pede a LLM um diagnostico estruturado. O resultado
e uma SUGESTAO: o agente nunca altera codigo nem aprova o pipeline.

Uso:
    python agente/diagnosticar_falha.py --log pytest.log
    python agente/diagnosticar_falha.py --log pytest.log --somente-prompt
    python agente/diagnosticar_falha.py --log pytest.log --publicar   # comenta no MR/PR

Variaveis de ambiente:
    ANTHROPIC_API_KEY   credencial da API (sem ela, gera so o prompt)
    GENAI_MODEL         modelo (padrao: claude-opus-5-5)
    GITLAB_API_TOKEN    token para comentar no Merge Request (GitLab CI)
    GITHUB_TOKEN        token para comentar no Pull Request (GitHub Actions)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELO_PADRAO = "claude-opus-5-5"
LIMITE_LOG = 40_000  # caracteres da secao de falhas enviados a LLM
LIMITE_ARQUIVO = 20_000  # caracteres por arquivo-fonte anexado
AVISO = (
    "> 🤖 **Diagnóstico gerado por IA generativa.** É uma sugestão: "
    "valide a causa e a correção antes de aplicar."
)

SYSTEM_PROMPT = """\
Você é um engenheiro DevOps sênior que diagnostica falhas de pipelines de CI em projetos Python.

Regras:
- Baseie-se apenas no log e no código fornecidos. Não invente arquivos, funções, variáveis ou linhas.
- Separe o que o log prova do que é hipótese.
- Procure a causa raiz, não só a linha onde a exceção estourou. Se a correção mais simples tratar só o sintoma, diga isso.
- Não proponha relaxar, pular ou apagar testes para o pipeline passar, a menos que o teste esteja comprovadamente errado; nesse caso, justifique.
- Responda em português do Brasil, em Markdown, usando exatamente as seções pedidas.
"""

FORMATO_RESPOSTA = """\
Responda com estas seções, nesta ordem:

## Resumo
Uma ou duas frases: o que falhou e por quê.

## Evidências no log
Trechos curtos do log (com teste e linha) que sustentam o diagnóstico.

## Causa raiz
Arquivo, linha e explicação. Diga se há diferença entre onde o erro estoura e onde ele nasce.

## Correção sugerida
Um diff unificado mínimo contra os arquivos fornecidos.

## Como validar
Comandos e testes que confirmam a correção.

## Confiança e premissas
Nível de confiança (alta, média ou baixa) e o que você assumiu sem poder verificar.

## Prevenção
No máximo três medidas para evitar a recorrência.
"""

PADROES_SEGREDO = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"glpat-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(
        r"(?i)\b((?:api[_-]?key|token|secret|password|senha)[\w-]*)\s*([=:])\s*['\"]?[^\s'\"]{6,}"
    ),
]


def mascarar_segredos(texto: str) -> str:
    for padrao in PADROES_SEGREDO:
        if padrao.groups >= 2:
            texto = padrao.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", texto)
        else:
            texto = padrao.sub("[REDACTED]", texto)
    return texto


def extrair_secao_falhas(log: str) -> tuple[str, bool]:
    """Recorta do cabecalho FAILURES/ERRORS ate o fim do log (inclui o resumo)."""
    inicio = re.search(r"^=+ (FAILURES|ERRORS) =+$", log, flags=re.MULTILINE)
    trecho = log[inicio.start():] if inicio else log
    if len(trecho) <= LIMITE_LOG:
        return trecho, False
    # Mantem o fim (resumo e ultimos tracebacks), que e onde esta a causa imediata.
    return trecho[-LIMITE_LOG:], True


def arquivos_citados(log: str, raiz: Path) -> list[Path]:
    """Arquivos .py do projeto mencionados no traceback, em ordem de aparicao."""
    candidatos = re.findall(r"([\w./\\-]+\.py):\d+", log)
    candidatos += re.findall(r'File "([^"]+\.py)", line \d+', log)
    vistos: list[Path] = []
    raiz = raiz.resolve()
    for nome in candidatos:
        caminho = Path(nome)
        caminho = (caminho if caminho.is_absolute() else raiz / caminho).resolve()
        try:
            caminho.relative_to(raiz)
        except ValueError:
            continue  # fora do projeto (site-packages, stdlib)
        if caminho.is_file() and caminho not in vistos:
            vistos.append(caminho)
    return vistos


def modulos_importados(arquivos: list[Path], raiz: Path) -> list[Path]:
    """Modulos do proprio projeto importados pelos arquivos citados (um nivel).

    O traceback mostra onde o erro estoura; a origem costuma estar num modulo
    importado que nunca aparece no log (ex.: a configuracao).
    """
    raiz = raiz.resolve()
    extras: list[Path] = []
    for arquivo in arquivos:
        codigo = arquivo.read_text(encoding="utf-8")
        nomes = re.findall(r"^\s*from\s+([\w.]+)\s+import", codigo, flags=re.MULTILINE)
        nomes += re.findall(r"^\s*import\s+([\w.]+)", codigo, flags=re.MULTILINE)
        for nome in nomes:
            base = raiz / Path(*nome.split("."))
            for candidato in (base.with_suffix(".py"), base / "__init__.py"):
                if candidato.is_file() and candidato not in arquivos and candidato not in extras:
                    extras.append(candidato)
                    break
    return extras


def anonimizar_caminhos(texto: str, raiz: Path) -> str:
    """Troca caminhos absolutos da maquina por marcadores (nao vazar usuario/host)."""
    for caminho, marcador in ((raiz.resolve(), "<projeto>"), (Path.home(), "<home>")):
        for variante in {str(caminho), caminho.as_posix()}:
            texto = texto.replace(variante, marcador)
    return texto


def contexto_ci() -> str:
    campos = {
        "Plataforma": "GitLab CI" if os.getenv("GITLAB_CI") else (
            "GitHub Actions" if os.getenv("GITHUB_ACTIONS") else "execução local"
        ),
        "Job": os.getenv("CI_JOB_NAME") or os.getenv("GITHUB_JOB"),
        "Commit": os.getenv("CI_COMMIT_SHA") or os.getenv("GITHUB_SHA"),
        "Branch": os.getenv("CI_COMMIT_REF_NAME") or os.getenv("GITHUB_REF_NAME"),
        "Python": sys.version.split()[0],
    }
    return "\n".join(f"- {k}: {v}" for k, v in campos.items() if v)


def montar_prompt(log: str, raiz: Path, incluir_imports: bool = True) -> str:
    falhas, truncado = extrair_secao_falhas(log)
    partes = [
        "O pipeline de CI falhou na etapa de testes automatizados (pytest).",
        "",
        "### Contexto da execução",
        contexto_ci(),
        "",
        "### Log do pytest (seção de falhas)",
    ]
    if truncado:
        partes.append(
            f"(Atenção: o log foi recortado para os últimos {LIMITE_LOG} caracteres.)"
        )
    partes += ["```text", falhas.rstrip(), "```", ""]

    citados = arquivos_citados(log, raiz)
    importados = modulos_importados(citados, raiz) if incluir_imports else []
    if citados:
        partes.append("### Código-fonte")
        partes.append(
            "Arquivos citados no traceback"
            + (" e módulos do projeto importados por eles." if importados else ".")
        )
        partes.append("")
    for caminho in citados + importados:
        conteudo = caminho.read_text(encoding="utf-8")
        rel = caminho.relative_to(raiz.resolve()).as_posix()
        aviso = ""
        if len(conteudo) > LIMITE_ARQUIVO:
            conteudo = conteudo[:LIMITE_ARQUIVO]
            aviso = f" (recortado nos primeiros {LIMITE_ARQUIVO} caracteres)"
        numerado = "\n".join(
            f"{i:4d} | {linha}" for i, linha in enumerate(conteudo.splitlines(), start=1)
        )
        partes += [f"#### `{rel}`{aviso}", "```python", numerado, "```", ""]

    partes.append(FORMATO_RESPOSTA)
    return anonimizar_caminhos(mascarar_segredos("\n".join(partes)), raiz)


def chamar_llm(prompt: str, modelo: str) -> tuple[str | None, str]:
    """Devolve (texto, situacao). texto=None quando a analise nao foi possivel."""
    try:
        import anthropic
    except ImportError:
        return None, "pacote `anthropic` não instalado"

    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError as erro:
        return None, f"sem credencial da API ({erro.__class__.__name__})"
    # O cliente resolve chave, token ou perfil (`ant auth login`); se nada foi
    # encontrado, o SDK so reclamaria na hora da requisicao.
    if not (client.api_key or client.auth_token or client.credentials):
        return None, "sem credencial da API (defina ANTHROPIC_API_KEY)"

    try:
        resposta = client.beta.messages.create(
            model=modelo,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium"},
            # Se o modelo recusar por politica de seguranca, a API refaz a chamada
            # num modelo alternativo escolhido pelo proprio servidor.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        return None, "credencial da API inválida"
    except anthropic.RateLimitError:
        return None, "limite de uso da API atingido (429)"
    except anthropic.APIStatusError as erro:
        return None, f"erro da API ({erro.status_code})"
    except anthropic.APIConnectionError:
        return None, "falha de conexão com a API"

    if resposta.stop_reason == "refusal":
        return None, "o modelo recusou a solicitação"
    texto = "\n".join(b.text for b in resposta.content if b.type == "text").strip()
    if resposta.stop_reason == "max_tokens":
        texto += "\n\n_(Resposta cortada pelo limite de tokens.)_"
    uso = resposta.usage
    return texto, f"{resposta.model}, {uso.input_tokens} tokens de entrada / {uso.output_tokens} de saída"


def montar_relatorio(diagnostico: str | None, situacao: str, arquivo_prompt: str) -> str:
    cabecalho = ["# 🤖 Análise automática de falha (GenAI)", "", AVISO, ""]
    if diagnostico is None:
        return "\n".join(
            cabecalho
            + [
                f"**Análise com IA não executada:** {situacao}.",
                "",
                f"O prompt completo foi salvo em `{arquivo_prompt}`. Ele pode ser "
                "revisado e enviado manualmente a uma LLM.",
                "",
            ]
        )
    return "\n".join(cabecalho + [diagnostico, "", "---", f"_Modelo: {situacao}_", ""])


def _post_json(url: str, corpo: dict, cabecalhos: dict) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", **cabecalhos},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def publicar(relatorio: str) -> str:
    """Publica o diagnostico no MR (GitLab) ou PR (GitHub), se houver contexto."""
    if os.getenv("GITLAB_CI"):
        iid, projeto = os.getenv("CI_MERGE_REQUEST_IID"), os.getenv("CI_PROJECT_ID")
        token = os.getenv("GITLAB_API_TOKEN")
        if not (iid and projeto and token):
            return "GitLab: sem Merge Request ou sem GITLAB_API_TOKEN; nada publicado"
        url = f"{os.environ['CI_API_V4_URL']}/projects/{projeto}/merge_requests/{iid}/notes"
        _post_json(url, {"body": relatorio}, {"PRIVATE-TOKEN": token})
        return f"comentário publicado no Merge Request !{iid}"

    if os.getenv("GITHUB_ACTIONS"):
        evento_path, token = os.getenv("GITHUB_EVENT_PATH"), os.getenv("GITHUB_TOKEN")
        evento = json.loads(Path(evento_path).read_text(encoding="utf-8")) if evento_path else {}
        numero = (evento.get("pull_request") or {}).get("number")
        if not (numero and token):
            return "GitHub: execução fora de Pull Request ou sem GITHUB_TOKEN; nada publicado"
        url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{numero}/comments"
        _post_json(
            url,
            {"body": relatorio},
            {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        return f"comentário publicado no Pull Request #{numero}"

    return "execução local; nada publicado"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", required=True, type=Path, help="log do pytest")
    parser.add_argument("--raiz", default=Path("."), type=Path, help="raiz do projeto")
    parser.add_argument("--saida", default=Path("diagnostico.md"), type=Path)
    parser.add_argument("--prompt-saida", default=Path("prompt-enviado.md"), type=Path)
    parser.add_argument("--somente-prompt", action="store_true", help="não chama a API")
    parser.add_argument(
        "--sem-imports",
        action="store_true",
        help="anexa só os arquivos do traceback (contexto mínimo, para comparação)",
    )
    parser.add_argument("--publicar", action="store_true", help="comenta no MR/PR")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows

    if not args.log.is_file():
        print(f"Log não encontrado: {args.log}", file=sys.stderr)
        return 2

    log = args.log.read_text(encoding="utf-8", errors="replace")
    prompt = montar_prompt(log, args.raiz, incluir_imports=not args.sem_imports)
    args.prompt_saida.write_text(
        f"<!-- system -->\n{SYSTEM_PROMPT}\n<!-- user -->\n{prompt}\n", encoding="utf-8"
    )
    print(f"Prompt salvo em {args.prompt_saida} ({len(prompt)} caracteres).")

    if args.somente_prompt:
        diagnostico, situacao = None, "modo --somente-prompt"
    else:
        modelo = os.getenv("GENAI_MODEL", MODELO_PADRAO)
        diagnostico, situacao = chamar_llm(prompt, modelo)

    relatorio = montar_relatorio(diagnostico, situacao, args.prompt_saida.name)
    args.saida.write_text(relatorio, encoding="utf-8")
    print(f"Diagnóstico salvo em {args.saida} ({situacao}).")

    resumo = os.getenv("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write(relatorio + "\n")

    if args.publicar and diagnostico is not None:
        try:
            print(publicar(relatorio))
        except (urllib.error.URLError, OSError) as erro:
            print(f"Falha ao publicar o comentário: {erro}", file=sys.stderr)

    # O agente nunca decide o status do pipeline: quem falha e o job de testes.
    return 0


if __name__ == "__main__":
    sys.exit(main())
