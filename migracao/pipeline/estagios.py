"""As etapas do pipeline de migração Adobe Flex -> Apache Royale (HTML5)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from . import integracao, validacoes
from .agentes import Agente, carregar_prompt, criar_cliente
from .etapas import Contexto, Etapa, Validacao
from .ferramentas import (FERRAMENTA_ESCREVER, FERRAMENTA_LER, FERRAMENTA_LISTAR, FERRAMENTA_SUBSTITUIR,
                          ErroFerramenta, SistemaArquivos, definicao, executores_basicos)
from .inventario import inventariar
from .royale import compilar_flex, compilar_royale

RAIZ = Path(__file__).resolve().parent.parent          # pasta migracao/
CONHECIMENTO = RAIZ / "conhecimento"
PROMPTS = RAIZ / "prompts"
TEMPLATES = RAIZ / "templates" / "html5"


def _versao_java(java_home: Path | None) -> str:
    java = str(java_home / "bin" / "java") if java_home else "java"
    try:
        saida = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=30)
        texto = (saida.stderr or saida.stdout)
        linha = next((l for l in texto.splitlines() if "version" in l), texto.strip())
        return linha.strip()
    except Exception as exc:
        return f"indisponível ({exc})"


def _major_java(versao: str) -> int:
    m = re.search(r'version "(\d+)(?:\.(\d+))?', versao)
    if not m:
        return 0
    major = int(m.group(1))
    return int(m.group(2) or 0) if major == 1 else major


# ============================================================================ 01 preparação

class Preparacao(Etapa):
    numero, nome = 1, "preparacao"
    titulo = "Preparação do ambiente"
    descricao = "confere ferramentas (Flex SDK, Royale SDK, Java, API Claude) e inventaria o código Flex"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        java_royale = _versao_java(c.java_royale)
        java_padrao = _versao_java(None)
        ctx.reg.info("ambiente.java", f"Java padrão (Flex SDK): {java_padrao}")
        ctx.reg.info("ambiente.java", f"Java do Royale: {java_royale}")

        inventario = inventariar(c.origem)
        ctx.dados["inventario"] = inventario
        ctx.reg.salvar_json("inventario-flex.json", inventario)
        ctx.reg.info("inventario", f"{inventario['total_arquivos']} arquivo(s), {inventario['total_linhas']} linhas, "
                                   f"{len(inventario['componentes_flex'])} tipos de componente Flex, "
                                   f"endpoints: {inventario['urls_api']}")
        for arq in inventario["arquivos"]:
            ctx.reg.debug("inventario.arquivo", f"{arq['caminho']} ({arq['bytes']} bytes, sha256 {arq['sha256'][:12]}…)")

        # prepara a pasta do projeto HTML5
        c.destino.mkdir(parents=True, exist_ok=True)
        for sub in ("src", "bin", "www", "template"):
            alvo = c.destino / sub
            if alvo.exists():
                shutil.rmtree(alvo)
                ctx.reg.info("destino.limpeza", f"removida a versão anterior de {sub}/")
        (c.destino / "src").mkdir()
        (c.destino / "template").mkdir()
        titulo = ctx.dados.get("titulo_app", Path(c.arquivo_principal).stem)
        template = (CONHECIMENTO / "index-template.html").read_text(encoding="utf-8").replace("__TITULO__", titulo)
        (c.destino / "template" / "index-template.html").write_text(template, encoding="utf-8")

        return {
            "modo": c.modo, "modelo": c.modelo, "java_flex": java_padrao, "java_royale": java_royale,
            "flex_home": str(c.flex_home) if c.flex_home else None,
            "royale_home": str(c.royale_home) if c.royale_home else None,
            "origem": str(c.origem), "destino": str(c.destino),
            "arquivos_flex": [a["caminho"] for a in inventario["arquivos"]],
            "componentes_flex": inventario["componentes_flex"], "endpoints": inventario["urls_api"],
        }

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        c = ctx.config
        inv = ctx.dados["inventario"]
        v = [
            Validacao("Projeto Flex encontrado", (c.origem / "src" / c.arquivo_principal).is_file(),
                      str(c.origem / "src" / c.arquivo_principal)),
            Validacao("Código Flex inventariado", inv["total_arquivos"] > 0, f"{inv['total_arquivos']} arquivo(s)"),
            Validacao("Apache Royale instalado no container",
                      bool(c.royale_home) and (c.royale_home / "js" / "bin" / "mxmlc").is_file(),
                      str(c.royale_home)),
            Validacao("Java 11+ disponível para o Royale", _major_java(r["java_royale"]) >= 11, r["java_royale"]),
            Validacao("Apache Flex SDK instalado no container",
                      bool(c.flex_home) and (c.flex_home / "lib" / "mxmlc.jar").is_file(),
                      str(c.flex_home), severidade="aviso"),
        ]
        if c.modo == "claude":
            v.append(Validacao("Chave da Claude Platform configurada", bool(os.environ.get("ANTHROPIC_API_KEY")),
                               "variável ANTHROPIC_API_KEY"))
            try:
                import anthropic
                v.append(Validacao("SDK anthropic instalado", True, anthropic.__version__))
            except ImportError:
                v.append(Validacao("SDK anthropic instalado", False, "pip install anthropic"))
        return v


# ============================================================================ 02 baseline Flex

class BaselineFlex(Etapa):
    numero, nome = 2, "baseline-flex"
    titulo = "Compilação de referência do Flex"
    descricao = "compila o código Flex original com o Apache Flex SDK para garantir que a origem é válida"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        if not c.flex_home or not (c.flex_home / "lib" / "mxmlc.jar").is_file():
            ctx.reg.aviso("flex.ausente", "Flex SDK não encontrado; etapa de baseline ignorada")
            return {"executada": False}
        swf = c.execucao / "baseline" / (Path(c.arquivo_principal).stem + ".swf")
        ctx.reg.info("flex.compilar", f"mxmlc (Flex SDK) em {c.origem}/src/{c.arquivo_principal}")
        r = compilar_flex(c.flex_home, c.origem, c.arquivo_principal, swf)
        ctx.reg.salvar_texto("baseline/mxmlc-flex.log", r.saida)
        ctx.reg.info("flex.resultado", r.resumo())
        return {"executada": True, "sucesso": r.sucesso, "codigo_saida": r.codigo_saida,
                "duracao_s": round(r.duracao_s, 1), "artefatos": r.artefatos, "erros": [e.mensagem for e in r.erros]}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        if not r.get("executada"):
            return [Validacao("Baseline Flex executada", False, "Flex SDK ausente", severidade="aviso")]
        return [Validacao("Código Flex original compila (SWF gerado)", r["sucesso"],
                          ", ".join(r["artefatos"]) or "; ".join(r["erros"][:3]))]


# ============================================================================ agentes: fábrica

FERRAMENTA_REGISTRAR_ANALISE = definicao(
    "registrar_analise",
    "Registra a análise estruturada da aplicação Flex. Encerra a tarefa de análise.",
    {
        "resumo": {"type": "string", "description": "O que a aplicação faz, em 3 a 6 frases"},
        "arquivos": {"type": "array", "description": "Plano de arquivos origem -> destino", "items": {
            "type": "object", "properties": {
                "origem": {"type": "string", "description": "caminho relativo a flex/, ex.: Agenda.mxml"},
                "destino": {"type": "string", "description": "ex.: royale/src/Agenda.mxml"},
                "papel": {"type": "string"}},
            "required": ["origem", "destino", "papel"]}},
        "componentes": {"type": "array", "description": "Todo componente Flex usado e o equivalente Royale", "items": {
            "type": "object", "properties": {
                "flex": {"type": "string", "description": "ex.: mx:DataGrid"},
                "royale": {"type": "string", "description": "ex.: j:DataGrid"},
                "observacao": {"type": "string"}},
            "required": ["flex", "royale"]}},
        "servicos": {"type": "array", "description": "Operações da API REST usadas", "items": {
            "type": "object", "properties": {
                "operacao": {"type": "string"}, "metodo_http": {"type": "string"},
                "url": {"type": "string", "description": "caminho, ex.: /contatos/{id}"},
                "contrato": {"type": "string", "description": "parâmetros, corpo e resposta"}},
            "required": ["operacao", "metodo_http", "url"]}},
        "logica": {"type": "array", "description": "Funções/handlers e o que fazem", "items": {
            "type": "object", "properties": {"nome": {"type": "string"}, "arquivo": {"type": "string"},
                                             "descricao": {"type": "string"}},
            "required": ["nome", "descricao"]}},
        "bindings": {"type": "array", "items": {"type": "string"}},
        "riscos": {"type": "array", "items": {"type": "object", "properties": {
            "descricao": {"type": "string"}, "mitigacao": {"type": "string"}}, "required": ["descricao"]}},
        "plano_conversao": {"type": "array", "items": {"type": "string"}, "description": "Passos da conversão"},
    },
    ["resumo", "arquivos", "componentes", "servicos", "logica", "riscos", "plano_conversao"])

FERRAMENTA_CONCLUIR_CONVERSAO = definicao(
    "concluir_conversao",
    "Informa que todos os arquivos Royale foram gravados em royale/src/. Encerra a tarefa de conversão.",
    {"resumo": {"type": "string"},
     "arquivos": {"type": "array", "items": {"type": "string"}, "description": "arquivos gravados"},
     "decisoes": {"type": "array", "items": {"type": "string"}, "description": "decisões de mapeamento relevantes"},
     "pendencias": {"type": "array", "items": {"type": "string"}, "description": "o que não teve equivalente"}},
    ["resumo", "arquivos"])

FERRAMENTA_COMPILAR = definicao(
    "compilar_royale",
    "Executa o compilador mxmlc do Apache Royale (JSRoyale) sobre royale/src/ e devolve o resultado.",
    {}, [])

FERRAMENTA_CONCLUIR_COMPILACAO = definicao(
    "concluir_compilacao",
    "Encerra o trabalho de compilação, listando as correções feitas.",
    {"resumo": {"type": "string"},
     "correcoes": {"type": "array", "items": {"type": "object", "properties": {
         "arquivo": {"type": "string"}, "erro": {"type": "string"}, "correcao": {"type": "string"}},
         "required": ["arquivo", "correcao"]}},
     "compilou": {"type": "boolean"}},
    ["resumo", "correcoes", "compilou"])


def _cliente(ctx: Contexto):
    if "cliente" not in ctx.dados:
        ctx.dados["cliente"] = criar_cliente(ctx.config.modo)
    return ctx.dados["cliente"]


def _sistema(nome_prompt: str) -> List[Dict[str, Any]]:
    guia = (CONHECIMENTO / "guia-royale-jewel.md").read_text(encoding="utf-8")
    return [
        {"type": "text", "text": carregar_prompt(PROMPTS, nome_prompt)},
        {"type": "text", "text": "# Base de conhecimento (guia/guia-royale-jewel.md)\n\n" + guia},
    ]


def _agente_analista(ctx: Contexto) -> Agente:
    if "agente_analista" in ctx.dados:
        return ctx.dados["agente_analista"]
    c = ctx.config
    fs = SistemaArquivos({"flex": c.origem / "src", "royale": c.destino, "guia": CONHECIMENTO},
                         ["royale"], ctx.reg, "analista-flex")
    executores = executores_basicos(fs)
    fase = {"atual": "analise"}
    ctx.dados["fase_analista"] = fase

    def so_na_conversao(nome: str):
        original = executores[nome]

        def executor(args: Dict[str, Any]) -> str:
            if fase["atual"] != "conversao":
                raise ErroFerramenta(f"{nome} só pode ser usado na TAREFA 2 (conversão). "
                                     "Agora conclua a análise com registrar_analise.")
            return original(args)
        return executor

    for nome in ("escrever_arquivo", "substituir_trecho"):
        executores[nome] = so_na_conversao(nome)

    # O conjunto de ferramentas é o MESMO nas duas tarefas: as ferramentas fazem parte do prefixo
    # do prompt, e mudá-las entre a análise e a conversão invalidaria o cache (prompt caching).
    # O que muda por tarefa é só a ferramenta de conclusão aceita (ferramentas_finais).
    agente = Agente(
        nome="analista-flex",
        papel="lê e analisa o código Flex e o converte para MXML/AS3 Royale",
        system=_sistema("agente-analista-flex.md"),
        ferramentas=[FERRAMENTA_LISTAR, FERRAMENTA_LER, FERRAMENTA_ESCREVER, FERRAMENTA_SUBSTITUIR,
                     FERRAMENTA_REGISTRAR_ANALISE, FERRAMENTA_CONCLUIR_CONVERSAO],
        executores=executores,
        ferramentas_finais=["registrar_analise"],
        ferramentas_fora_de_fase={"concluir_conversao": "concluir_conversao só vale na TAREFA 2 (conversão). "
                                                        "Agora conclua a análise com registrar_analise."},
        pensamento_tokens=c.pensamento_tokens,
    )
    ctx.dados["agente_analista"] = agente
    ctx.dados["fs_analista"] = fs
    return agente


# ============================================================================ 03 análise

class AnaliseFlex(Etapa):
    numero, nome = 3, "analise"
    titulo = "Análise do código Flex (Agente Analista)"
    descricao = "o agente lê MXML/AS3 e registra componentes, lógica, serviços, riscos e o plano de conversão"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        inv = ctx.dados["inventario"]
        agente = _agente_analista(ctx)
        resumo_inv = {
            "arquivos": [a["caminho"] for a in inv["arquivos"]],
            "componentes_flex": inv["componentes_flex"],
            "endpoints_detectados": inv["urls_api"],
        }
        tarefa = (
            "TAREFA 1 de 2: ANÁLISE.\n\n"
            f"Analise a aplicação Adobe Flex em flex/ (arquivo principal: flex/{c.arquivo_principal}).\n"
            "Leia TODOS os arquivos de código (use listar_arquivos e ler_arquivo). O guia "
            "guia/guia-royale-jewel.md já está no seu system prompt; não precisa lê-lo de novo.\n"
            "Em 'componentes', use uma entrada por componente Flex (ex.: 'mx:DataGrid'), sem agrupar.\n"
            "Depois chame registrar_analise com a análise completa. O plano de arquivos deve mapear cada "
            "arquivo de flex/ para royale/src/ com o mesmo caminho relativo.\n\n"
            "Inventário estático feito pelo pipeline (para conferência):\n"
            + json.dumps(resumo_inv, ensure_ascii=False, indent=2)
        )

        def validar_final(_nome: str, analise: Dict[str, Any]):
            return validacoes.texto_recusa(validacoes.validar_analise(analise, inv, c.arquivo_principal)) or None

        resultado = agente.executar(ctx, _cliente(ctx), tarefa, validar_final)
        ctx.dados["analise"] = resultado.dados_finais
        if resultado.concluido:
            ctx.reg.salvar_json("analise-agente.json", resultado.dados_finais)
            ctx.reg.info("analise.resumo", str(resultado.dados_finais.get("resumo", ""))[:500])
        return {"concluido": resultado.concluido, "turnos": resultado.turnos,
                "chamadas_ferramentas": resultado.chamadas_ferramentas, "uso_tokens": resultado.uso_tokens,
                "componentes_mapeados": len(resultado.dados_finais.get("componentes", [])),
                "servicos": len(resultado.dados_finais.get("servicos", [])),
                "riscos": len(resultado.dados_finais.get("riscos", []))}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        v = [Validacao("Agente analista concluiu a análise", r["concluido"])]
        if r["concluido"]:
            v += validacoes.validar_analise(ctx.dados["analise"], ctx.dados["inventario"], ctx.config.arquivo_principal)
        return v


# ============================================================================ 04 conversão

class ConversaoRoyale(Etapa):
    numero, nome = 4, "conversao"
    titulo = "Conversão para MXML/AS3 Royale (Agente Analista)"
    descricao = "o mesmo agente, com a análise em contexto, reescreve o código para Apache Royale / Jewel"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        agente = _agente_analista(ctx)
        fs: SistemaArquivos = ctx.dados["fs_analista"]
        ctx.dados["fase_analista"]["atual"] = "conversao"
        agente.ferramentas_finais = ["concluir_conversao"]
        agente.ferramentas_fora_de_fase = {"registrar_analise": "A análise já foi registrada e aprovada. "
                                                                "Agora grave os arquivos e chame concluir_conversao."}
        tarefa = (
            "TAREFA 2 de 2: CONVERSÃO.\n\n"
            "Com base na sua análise (já registrada e aprovada), escreva o código Apache Royale (Jewel) "
            "equivalente em royale/src/, seguindo o plano de arquivos e o guia. Grave um arquivo por "
            "chamada de escrever_arquivo, com o conteúdo completo. Ao terminar, chame concluir_conversao."
        )
        src = c.destino / "src"
        avisos_de_layout_enviados = {"feito": False}

        def validar_final(_nome: str, _dados: Dict[str, Any]):
            resultado_val = validacoes.validar_codigo_royale(src, ctx.dados["analise"], ctx.dados["inventario"],
                                                             c.arquivo_principal)
            falhas = [x for x in resultado_val if not x.ok and x.severidade == "bloqueante"]
            # avisos de layout (ex.: Card com height fixo cortando o formulário) são devolvidos ao
            # agente UMA vez, para ele corrigir; se insistir, viram só aviso no relatório
            layout = [x for x in resultado_val if not x.ok and x.severidade == "aviso" and "j:Card" in x.nome]
            if layout and not avisos_de_layout_enviados["feito"]:
                avisos_de_layout_enviados["feito"] = True
                falhas += layout
            if not falhas:
                return None
            return ("A conversão foi recusada pelo validador estático do pipeline. Corrija os arquivos e chame "
                    "concluir_conversao de novo:\n" + "\n".join(f"- {x.nome}: {x.detalhe}" for x in falhas))

        resultado = agente.executar(ctx, _cliente(ctx), tarefa, validar_final)
        ctx.dados["conversao"] = resultado.dados_finais
        ctx.reg.salvar_json("conversao-agente.json", resultado.dados_finais)
        for d in resultado.dados_finais.get("decisoes", []) or []:
            ctx.reg.info("conversao.decisao", str(d))
        for p in resultado.dados_finais.get("pendencias", []) or []:
            ctx.reg.aviso("conversao.pendencia", str(p))
        return {"concluido": resultado.concluido, "turnos": resultado.turnos,
                "chamadas_ferramentas": resultado.chamadas_ferramentas, "uso_tokens": resultado.uso_tokens,
                "arquivos_escritos": fs.escritos}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        c = ctx.config
        v = [Validacao("Agente concluiu a conversão", r["concluido"])]
        v += validacoes.validar_codigo_royale(c.destino / "src", ctx.dados.get("analise", {}),
                                              ctx.dados["inventario"], c.arquivo_principal)
        return v


# ============================================================================ 05 compilação assistida

class CompilacaoRoyale(Etapa):
    numero, nome = 5, "compilacao"
    titulo = "Compilação Royale assistida (Agente Assistente do Compilador)"
    descricao = "o Royale traduz MXML/AS3 para HTML5/CSS/JS; o agente corrige o que o compilador rejeitar"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        tentativas: List[Dict[str, Any]] = []

        def compilar(origem: str) -> Any:
            n = len(tentativas) + 1
            ctx.reg.info("royale.compilar", f"tentativa {n} ({origem})")
            r = compilar_royale(c.royale_home, c.destino, c.arquivo_principal, c.java_royale)
            ctx.reg.salvar_texto(f"compilacao/tentativa-{n:02d}.log", "$ " + " ".join(r.comando) + "\n\n" + r.saida)
            tentativas.append({"tentativa": n, "origem": origem, "sucesso": r.sucesso, "erros": len(r.erros),
                               "avisos": len(r.avisos), "duracao_s": round(r.duracao_s, 1),
                               "diagnosticos": [d.como_dict() for d in (r.erros + r.avisos)[:40]]})
            (ctx.reg.ok if r.sucesso else ctx.reg.aviso)("royale.resultado", r.resumo(8))
            return r

        resultado = compilar("pipeline")
        agente_usado = False
        conclusao: Dict[str, Any] = {}
        uso: Dict[str, int] = {}

        if not resultado.sucesso:
            agente_usado = True
            fs = SistemaArquivos({"royale": c.destino, "guia": CONHECIMENTO, "flex": c.origem / "src"},
                                 ["royale"], ctx.reg, "assistente-compilador")
            executores = executores_basicos(fs)
            estado = {"ultimo": resultado}

            def ferramenta_compilar(_args: Dict[str, Any]) -> str:
                if len(tentativas) >= c.max_tentativas_compilacao:
                    return (f"Limite de {c.max_tentativas_compilacao} compilações atingido. "
                            "Chame concluir_compilacao agora.")
                estado["ultimo"] = compilar("agente")
                return estado["ultimo"].resumo()

            executores["compilar_royale"] = ferramenta_compilar
            agente = Agente(
                nome="assistente-compilador",
                papel="auxilia o compilador Apache Royale corrigindo o código MXML/AS3",
                system=_sistema("agente-assistente-compilador.md"),
                ferramentas=[FERRAMENTA_LISTAR, FERRAMENTA_LER, FERRAMENTA_ESCREVER, FERRAMENTA_SUBSTITUIR,
                             FERRAMENTA_COMPILAR, FERRAMENTA_CONCLUIR_COMPILACAO],
                executores=executores,
                ferramentas_finais=["concluir_compilacao"],
                max_turnos=4 * c.max_tentativas_compilacao + 10,
                pensamento_tokens=c.pensamento_tokens,
            )
            tarefa = (
                "O compilador Apache Royale rejeitou o código em royale/src/ "
                f"(arquivo principal: royale/src/{c.arquivo_principal}). Os caminhos dos diagnósticos abaixo "
                "são relativos a royale/ (ex.: src/Agenda.mxml = royale/src/Agenda.mxml).\n\n"
                + resultado.resumo(40)
                + f"\n\nCorrija e recompile com compilar_royale (limite total de {c.max_tentativas_compilacao} "
                  "compilações). A versão Flex original está em flex/ para consulta. Ao final, chame concluir_compilacao."
            )
            r_agente = agente.executar(ctx, _cliente(ctx), tarefa)
            conclusao = r_agente.dados_finais
            uso = r_agente.uso_tokens
            for corr in conclusao.get("correcoes", []) or []:
                ctx.reg.info("compilacao.correcao", f"{corr.get('arquivo')}: {corr.get('correcao')}")
            # confirmação independente do pipeline
            if not estado["ultimo"].sucesso or tentativas[-1]["origem"] != "pipeline":
                resultado = compilar("verificação final do pipeline")
        else:
            ctx.reg.ok("compilacao.direta", "o código do Agente Analista compilou na primeira tentativa; "
                                            "o Agente Assistente do Compilador não foi necessário")

        ctx.dados["compilacao"] = resultado
        return {"sucesso": resultado.sucesso, "tentativas": tentativas, "agente_usado": agente_usado,
                "conclusao_agente": conclusao, "uso_tokens": uso, "artefatos": resultado.artefatos,
                "erros_finais": [d.formatar() for d in resultado.erros], "avisos_finais": len(resultado.avisos)}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        c = ctx.config
        nome = Path(c.arquivo_principal).stem
        release = c.destino / "bin" / "js-release"
        return [
            Validacao("Royale compilou sem erros", r["sucesso"], "; ".join(r["erros_finais"][:3])),
            Validacao("HTML5 gerado (index.html + JS + CSS)",
                      all((release / f).is_file() for f in ("index.html", f"{nome}.js")) and any(release.glob("*.css")),
                      ", ".join(r["artefatos"])),
            Validacao(f"Compilações dentro do limite ({c.max_tentativas_compilacao})",
                      len(r["tentativas"]) <= c.max_tentativas_compilacao + 1, f"{len(r['tentativas'])} tentativa(s)"),
            Validacao("Sem avisos do compilador", r["avisos_finais"] == 0, f"{r['avisos_finais']} aviso(s)",
                      severidade="aviso"),
        ]


# ============================================================================ 06 empacotamento

class Empacotamento(Etapa):
    numero, nome = 6, "empacotamento"
    titulo = "Empacotamento do projeto HTML5"
    descricao = "monta o projeto HTML5 (www/, nginx, Docker) apontando para a mesma API Java 7"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        release = c.destino / "bin" / "js-release"
        www = c.destino / "www"
        if www.exists():
            shutil.rmtree(www)
        shutil.copytree(release, www)
        ctx.reg.info("pacote.www", f"{len(list(www.iterdir()))} arquivo(s) copiados de bin/js-release para www/")

        projeto_flex = ctx.dados.get("nome_projeto_flex", "agenda-contatos")
        titulo = ctx.dados.get("titulo_app", Path(c.arquivo_principal).stem)
        nome_destino = c.destino.name if c.destino.name not in ("saida", "") else "agenda-contatos-html5"
        substituicoes = {
            "__PROJETO_FLEX__": projeto_flex,
            "__BACKEND__": "http://backend:8080",
            "__TITULO__": titulo,
            "__PORTA__": str(ctx.dados.get("porta_html5", 8082)),
            "__IMAGEM__": nome_destino,
            "__CONTAINER__": nome_destino,
            "__REDE__": f"{projeto_flex}_default",
        }
        gerados = []
        for modelo in ("Dockerfile", "nginx.conf", "docker-compose.yml"):
            texto = (TEMPLATES / modelo).read_text(encoding="utf-8")
            for k, val in substituicoes.items():
                texto = texto.replace(k, val)
            (c.destino / modelo).write_text(texto, encoding="utf-8")
            gerados.append(modelo)
        (c.destino / ".dockerignore").write_text("bin\nsrc\ntemplate\nlogs-migracao\n", encoding="utf-8")
        gerados.append(".dockerignore")
        ctx.reg.info("pacote.arquivos", "gerados: " + ", ".join(gerados))
        ctx.dados["substituicoes"] = substituicoes
        return {"www": sorted(p.name for p in www.iterdir()), "gerados": gerados, "parametros": substituicoes}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        # README é escrito no relatório final; aqui só conferimos o que já deveria existir
        return [x for x in validacoes.validar_pacote(ctx.config.destino, ctx.config.arquivo_principal)
                if x.nome != "README.md presente"]


# ============================================================================ 07 integração

class Integracao(Etapa):
    numero, nome = 7, "integracao"
    titulo = "Teste de integração com a API Java 7"
    descricao = "serve o HTML5 gerado e executa, pelo mesmo /api, as chamadas que a tela faz"

    def executar(self, ctx: Contexto) -> Dict[str, Any]:
        c = ctx.config
        if c.pular_integracao:
            ctx.reg.aviso("integracao.pulada", "teste de integração desativado (--pular-integracao)")
            return {"executado": False}
        v, evidencias = integracao.testar(c.destino / "www", c.arquivo_principal, c.api_base_teste, ctx.reg)
        ctx.dados["validacoes_integracao"] = v
        ctx.reg.salvar_json("integracao-evidencias.json", evidencias)
        return {"executado": True, "api": c.api_base_teste, "chamadas": len(evidencias["chamadas"])}

    def validar(self, ctx: Contexto, r: Dict[str, Any]) -> List[Validacao]:
        if not r.get("executado"):
            return [Validacao("Teste de integração executado", False, "desativado", severidade="aviso")]
        return ctx.dados["validacoes_integracao"]
