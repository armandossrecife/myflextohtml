#!/usr/bin/env python3
"""Pipeline de migração de telas Adobe Flex -> HTML5 com agentes da Claude Platform e Apache Royale.

Uso (dentro do container "migrador"):

    python3 migrar.py --origem /workspace/agenda-contatos/frontend \\
                      --destino /workspace/agenda-contatos-html5

Etapas (cada uma validada e registrada em execucoes/<id>/):
    01 preparacao     ambiente + inventário estático do código Flex
    02 baseline-flex  compila o Flex original com o Apache Flex SDK (prova que a origem é válida)
    03 analise        Agente Analista (Claude) lê e analisa MXML/AS3
    04 conversao      Agente Analista reescreve para MXML/AS3 Royale (Jewel)
    05 compilacao     Royale compila para HTML5/CSS/JS; Agente Assistente do Compilador corrige erros
    06 empacotamento  projeto HTML5 com nginx apontando /api para a mesma API Java 7
    07 integracao     serve o HTML5 e testa as chamadas reais na API Java 7
    relatório final   relatorio-migracao.md (sempre gerado)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import relatorio  # noqa: E402
from pipeline.estagios import (AnaliseFlex, BaselineFlex, CompilacaoRoyale, ConversaoRoyale,  # noqa: E402
                               Empacotamento, Integracao, Preparacao)
from pipeline.etapas import Config, Contexto, executar_pipeline  # noqa: E402
from pipeline.registro import Registro  # noqa: E402


def _caminho_env(nome: str) -> Path | None:
    valor = os.environ.get(nome)
    return Path(valor) if valor else None


def main() -> int:
    raiz = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origem", type=Path, default=raiz.parent / "frontend",
                   help="projeto Flex (pasta que contém src/). Padrão: ../frontend")
    p.add_argument("--destino", type=Path, default=raiz.parent.parent / "agenda-contatos-html5",
                   help="pasta do projeto HTML5 a ser gerado. Padrão: ../../agenda-contatos-html5")
    p.add_argument("--principal", default="Agenda.mxml", help="arquivo MXML principal (em src/)")
    p.add_argument("--titulo", default="Agenda de Contatos", help="título da aplicação HTML5")
    p.add_argument("--projeto-flex", default=os.environ.get("PROJETO_FLEX", "agenda-contatos"),
                   help="nome do projeto docker compose do Flex (a rede <nome>_default é reutilizada)")
    p.add_argument("--porta", type=int, default=8082, help="porta local da aplicação HTML5")
    p.add_argument("--modelo", default=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
                   help="modelo da Claude Platform (padrão: claude-sonnet-5 ou $CLAUDE_MODEL)")
    p.add_argument("--modo", choices=["claude", "simulado"], default=os.environ.get("MODO_MIGRACAO", "claude"),
                   help="'claude' usa a API real; 'simulado' ensaia o pipeline sem API (usa a referência)")
    p.add_argument("--tentativas", type=int, default=5, help="máximo de compilações na etapa 05")
    p.add_argument("--pensamento", type=int, default=0,
                   help="orçamento de extended thinking por turno (0 = desativado)")
    p.add_argument("--api-teste", default=os.environ.get("API_BASE_TESTE", "http://backend:8080/api"),
                   help="URL da API Java 7 usada no teste de integração")
    p.add_argument("--pular-integracao", action="store_true", help="não executa a etapa 07")
    p.add_argument("--verbose", action="store_true", help="mostra eventos DEBUG no console")
    args = p.parse_args()

    execucao = raiz / "execucoes" / datetime.now().strftime("%Y%m%d-%H%M%S")
    reg = Registro(execucao, "DEBUG" if args.verbose else "INFO")
    config = Config(
        origem=args.origem.resolve(), destino=args.destino.resolve(), execucao=execucao,
        modelo=args.modelo, modo=args.modo, max_tentativas_compilacao=args.tentativas,
        flex_home=_caminho_env("FLEX_HOME"), royale_home=_caminho_env("ROYALE_HOME"),
        java_royale=_caminho_env("ROYALE_JAVA_HOME"), api_base_teste=args.api_teste,
        arquivo_principal=args.principal, pular_integracao=args.pular_integracao,
        pensamento_tokens=args.pensamento,
    )
    ctx = Contexto(config=config, reg=reg)
    ctx.dados.update(titulo_app=args.titulo, nome_projeto_flex=args.projeto_flex, porta_html5=args.porta)

    reg.etapa_atual = "inicio"
    reg.info("pipeline.inicio", f"Migração Flex -> HTML5 | modo={config.modo} modelo={config.modelo}")
    reg.info("pipeline.config", f"origem={config.origem} destino={config.destino} logs={execucao}")

    etapas = [Preparacao(), BaselineFlex(), AnaliseFlex(), ConversaoRoyale(), CompilacaoRoyale(),
              Empacotamento(), Integracao()]

    def finalizar(resultados):
        caminho = relatorio.gerar(ctx, resultados)
        sucesso = all(r.status == "sucesso" for r in resultados)
        (reg.ok if sucesso else reg.erro)("pipeline.fim",
            ("MIGRAÇÃO CONCLUÍDA" if sucesso else "MIGRAÇÃO INCOMPLETA") + f" | relatório: {caminho}")

    resultados = executar_pipeline(ctx, etapas, finalizar)
    reg.fechar()
    return 0 if all(r.status == "sucesso" for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
