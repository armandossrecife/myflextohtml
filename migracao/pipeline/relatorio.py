"""Relatório final da migração (sempre gerado, mesmo quando uma etapa falha)."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .etapas import Contexto, ResultadoEtapa

ICONE = {"sucesso": "✅", "falhou": "❌", "erro": "💥", "pulada": "⏭️"}


def _tabela_etapas(resultados: List[ResultadoEtapa]) -> str:
    linhas = ["| Etapa | Status | Duração | Validações |", "|---|---|---|---|"]
    for r in resultados:
        ok = sum(1 for v in r.validacoes if v.ok)
        linhas.append(f"| {r.etapa} · {r.titulo} | {ICONE.get(r.status, '')} {r.status} | "
                      f"{r.duracao_s:.1f}s | {ok}/{len(r.validacoes)} |")
    return "\n".join(linhas)


def _validacoes(resultados: List[ResultadoEtapa]) -> str:
    partes = []
    for r in resultados:
        if not r.validacoes and not r.erro:
            continue
        partes.append(f"### {r.etapa} · {r.titulo}\n")
        for v in r.validacoes:
            marca = "✅" if v.ok else ("⚠️" if v.severidade == "aviso" else "❌")
            partes.append(f"- {marca} {v.nome}" + (f" — {v.detalhe}" if v.detalhe else ""))
        if r.erro:
            partes.append(f"- 💥 Exceção: `{r.erro}`")
        partes.append("")
    return "\n".join(partes)


def _tokens(ctx: Contexto) -> str:
    if not ctx.uso_tokens:
        return "Nenhuma chamada à API (modo simulado ou etapa não executada)."
    linhas = ["| Agente | Entrada | Saída | Cache (escrita) | Cache (leitura) |", "|---|---|---|---|---|"]
    for agente, u in ctx.uso_tokens.items():
        linhas.append(f"| {agente} | {u.get('input_tokens', 0):,} | {u.get('output_tokens', 0):,} | "
                      f"{u.get('cache_creation_input_tokens', 0):,} | {u.get('cache_read_input_tokens', 0):,} |")
    return "\n".join(linhas).replace(",", ".")


def _secao_analise(ctx: Contexto) -> str:
    a: Dict[str, Any] = ctx.dados.get("analise") or {}
    if not a:
        return "_Análise não disponível._"
    partes = [a.get("resumo", ""), "", "**Mapeamento de componentes**", "",
              "| Flex | Royale | Observação |", "|---|---|---|"]
    for comp in a.get("componentes", []):
        partes.append(f"| `{comp.get('flex')}` | `{comp.get('royale')}` | {comp.get('observacao', '')} |")
    partes += ["", "**Operações da API (contrato preservado)**", ""]
    for s in a.get("servicos", []):
        partes.append(f"- `{s.get('metodo_http')} {s.get('url')}` — {s.get('operacao')}")
    if a.get("riscos"):
        partes += ["", "**Riscos identificados**", ""]
        for r in a["riscos"]:
            partes.append(f"- {r.get('descricao')}" + (f" → {r.get('mitigacao')}" if r.get("mitigacao") else ""))
    return "\n".join(partes)


def _secao_compilacao(resultados: List[ResultadoEtapa]) -> str:
    r = next((x for x in resultados if x.etapa.endswith("compilacao")), None)
    if not r or not r.resultado:
        return "_Compilação não executada._"
    linhas = ["| Tentativa | Origem | Erros | Avisos | Resultado |", "|---|---|---|---|---|"]
    for t in r.resultado.get("tentativas", []):
        linhas.append(f"| {t['tentativa']} | {t['origem']} | {t['erros']} | {t['avisos']} | "
                      f"{'✅ compilou' if t['sucesso'] else '❌ falhou'} |")
    correcoes = (r.resultado.get("conclusao_agente") or {}).get("correcoes") or []
    if correcoes:
        linhas += ["", "**Correções feitas pelo Agente Assistente do Compilador**", ""]
        for c in correcoes:
            linhas.append(f"- `{c.get('arquivo')}`: {c.get('correcao')}" + (f" (erro: {c.get('erro')})" if c.get("erro") else ""))
    elif not r.resultado.get("agente_usado"):
        linhas += ["", "O código compilou na primeira tentativa; o Agente Assistente do Compilador não foi necessário."]
    return "\n".join(linhas)


def gerar(ctx: Contexto, resultados: List[ResultadoEtapa]) -> Path:
    c = ctx.config
    sucesso = bool(resultados) and all(r.status == "sucesso" for r in resultados)
    avisos = sum(1 for r in resultados for v in r.validacoes if not v.ok and v.severidade == "aviso")
    agora = datetime.now().astimezone()
    duracao = sum(r.duracao_s for r in resultados)
    porta = ctx.dados.get("porta_html5", 8082)

    md = f"""# Relatório de migração Adobe Flex → HTML5 (Apache Royale)

- **Resultado:** {"✅ MIGRAÇÃO CONCLUÍDA" if sucesso else "❌ MIGRAÇÃO INCOMPLETA"} ({avisos} aviso(s))
- **Execução:** `{c.execucao.name}` · {agora:%d/%m/%Y %H:%M} · duração total {duracao:.0f}s
- **Modo:** {c.modo} · **Modelo:** `{c.modelo}`
- **Origem (Flex):** `{c.origem}` → **Destino (HTML5):** `{c.destino}`

## Etapas

{_tabela_etapas(resultados)}

## Análise do Agente Analista

{_secao_analise(ctx)}

## Compilação Apache Royale

{_secao_compilacao(resultados)}

## Uso de tokens (Claude Platform)

{_tokens(ctx)}

## Validações

{_validacoes(resultados)}
## Arquivos de log

- `pipeline.log`: log legível com os eventos de todas as etapas
- `eventos.jsonl`: os mesmos eventos em JSON, um por linha
- `etapas/*.json`: resultado e validações de cada etapa
- `agentes/<agente>/turno-NN.json`: cada chamada à API (resposta completa e tokens)
- `compilacao/tentativa-NN.log`: saída completa do compilador Royale em cada tentativa
- `inventario-flex.json`, `analise-agente.json`, `conversao-agente.json`, `integracao-evidencias.json`
"""
    destino_rel = ctx.reg.salvar_texto("relatorio-migracao.md", md)
    ctx.reg.salvar_json("resumo.json", {"sucesso": sucesso, "avisos": avisos,
                                         "etapas": [r.como_dict() for r in resultados], "tokens": ctx.uso_tokens})

    # cópia dos logs e do relatório dentro do projeto HTML5
    if c.destino.exists():
        logs = c.destino / "logs-migracao"
        if logs.exists():
            shutil.rmtree(logs)
        shutil.copytree(c.execucao, logs, ignore=shutil.ignore_patterns("baseline"))
        shutil.copy2(destino_rel, c.destino / "relatorio-migracao.md")
        _readme(ctx, sucesso, porta)
    return destino_rel


def _readme(ctx: Contexto, sucesso: bool, porta: int) -> None:
    c = ctx.config
    s = ctx.dados.get("substituicoes", {})
    projeto_flex = s.get("__PROJETO_FLEX__", "agenda-contatos")
    titulo = ctx.dados.get("titulo_app", Path(c.arquivo_principal).stem)
    texto = f"""# {titulo} — versão HTML5 (Apache Royale)

Este projeto foi **gerado automaticamente** pelo pipeline de migração Adobe Flex → HTML5
(`{projeto_flex}/migracao`), usando dois agentes da Claude Platform e o compilador Apache Royale.
A aplicação roda direto no navegador (HTML5 + CSS + JavaScript), sem Flash Player nem Ruffle, e usa
**a mesma API REST Java 7** do projeto Flex, sem nenhuma alteração no backend.

Status da migração: {"✅ concluída" if sucesso else "❌ incompleta: veja relatorio-migracao.md"}

## Como executar

```bash
# 1. suba o projeto Flex original (backend Java 7 + MySQL + frontend Flex)
cd ../{projeto_flex}
docker compose up -d

# 2. suba a versão HTML5
cd ../{c.destino.name if c.destino.name != "saida" else "agenda-contatos-html5"}
docker compose up -d --build
```

| Aplicação | URL |
|---|---|
| Flex original (SWF via Ruffle) | http://localhost:8080 |
| **HTML5 migrada (Apache Royale)** | **http://localhost:{porta}** |
| API Java 7 (compartilhada) | http://localhost:8081/api/health |

O container desta aplicação entra na rede Docker `{projeto_flex}_default` e encaminha `/api` para o
serviço `backend` (Tomcat 7 / Java 7). Por isso o projeto Flex precisa estar no ar antes.

## Estrutura

```
src/                     código Royale (MXML + AS3) produzido pelos agentes
bin/js-release/          saída do compilador Royale
www/                     HTML5 + CSS + JS servidos pelo nginx
nginx.conf               arquivos estáticos + proxy /api -> backend:8080 (Java 7)
Dockerfile               imagem nginx com www/
docker-compose.yml       serviço frontend-html5 (porta {porta}) na rede do projeto Flex
relatorio-migracao.md    relatório da migração (etapas, validações, tokens)
logs-migracao/           logs completos da execução do pipeline
```

Para refazer a migração, rode o pipeline de novo a partir do projeto Flex (veja `{projeto_flex}/migracao/README.md`).
"""
    (c.destino / "README.md").write_text(texto, encoding="utf-8")
