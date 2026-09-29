"""Validações estáticas usadas pelas etapas (análise, código convertido, pacote HTML5)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

from .etapas import Validacao
from .inventario import NS_MX, NS_MX_2006, NS_SPARK, RE_FUNCAO, RE_IMPORT

ESTRUTURAIS = {"mx:columns", "mx:Script", "mx:Style", "mx:Declarations"}
RE_COMPONENTE = re.compile(r"\b(?:mx|s|fx):(\w+)")


# ---------------------------------------------------------------------- análise (Agente 1)

def validar_analise(analise: Dict[str, Any], inventario: Dict[str, Any], principal: str) -> List[Validacao]:
    v: List[Validacao] = []
    arquivos_origem = {a["caminho"] for a in inventario["arquivos"]}
    mapeados = {str(a.get("origem", "")).replace("flex/", "", 1) for a in analise.get("arquivos", [])}
    faltando = sorted(arquivos_origem - mapeados)
    v.append(Validacao("Todos os arquivos Flex estão no plano de conversão", not faltando,
                       f"faltando: {faltando}" if faltando else f"{len(arquivos_origem)} arquivo(s)"))

    destinos = [str(a.get("destino", "")) for a in analise.get("arquivos", [])]
    invalidos = [d for d in destinos if not re.match(r"^(royale/)?src/.+\.(mxml|as)$", d)]
    v.append(Validacao("Destinos apontam para royale/src/*.mxml|*.as", not invalidos,
                       f"inválidos: {invalidos}" if invalidos else ", ".join(destinos)))

    principal_ok = any(d.endswith("src/" + principal) for d in destinos)
    v.append(Validacao(f"Arquivo principal {principal} mantém o nome", principal_ok))

    # o agente pode agrupar ("mx:DataGrid + mx:DataGridColumn") ou anotar ("mx:Button label=");
    # extraímos cada nome de componente citado no texto
    citados = set()
    for c in analise.get("componentes", []):
        citados.update(RE_COMPONENTE.findall(str(c.get("flex", ""))))
    esperados = [c for c in inventario["componentes_flex"] if c not in ESTRUTURAIS]
    sem_mapa = [c for c in esperados if c.split(":")[-1] not in citados]
    v.append(Validacao("Todo componente Flex usado tem mapeamento para Royale", not sem_mapa,
                       f"sem mapeamento: {sem_mapa}" if sem_mapa else f"{len(esperados)} componente(s)"))

    servicos = analise.get("servicos", [])
    if inventario["urls_api"]:
        urls = " ".join(str(s.get("url", "")) for s in servicos)
        ausentes = [u for u in inventario["urls_api"] if u.rstrip("/") not in urls]
        v.append(Validacao("Endpoints da API identificados", bool(servicos) and not ausentes,
                           f"ausentes: {ausentes}" if ausentes else f"{len(servicos)} operação(ões)"))

    v.append(Validacao("Riscos e decisões registrados", bool(analise.get("riscos")), severidade="aviso",
                       detalhe=f"{len(analise.get('riscos', []))} risco(s)"))
    return v


def texto_recusa(validacoes: List[Validacao]) -> str:
    falhas = [f"- {x.nome}: {x.detalhe}" for x in validacoes if not x.ok and x.severidade == "bloqueante"]
    if not falhas:
        return ""
    return ("A análise foi recusada pelo validador do pipeline. Corrija e chame registrar_analise "
            "novamente com a análise completa:\n" + "\n".join(falhas))


# ---------------------------------------------------------------------- código Royale (Agente 1)

def _fontes(src: Path) -> List[Path]:
    return sorted(p for p in src.rglob("*") if p.suffix in (".mxml", ".as"))


def validar_codigo_royale(src_royale: Path, analise: Dict[str, Any], inventario: Dict[str, Any],
                          principal: str) -> List[Validacao]:
    v: List[Validacao] = []
    fontes = _fontes(src_royale)
    v.append(Validacao("Código Royale gerado", bool(fontes), f"{len(fontes)} arquivo(s)"))
    if not fontes:
        return v

    esperados = [re.sub(r"^(royale/)?src/", "", str(a.get("destino", ""))) for a in analise.get("arquivos", [])]
    ausentes = [e for e in esperados if e and not (src_royale / e).is_file()]
    v.append(Validacao("Todos os arquivos planejados foram gerados", not ausentes,
                       f"ausentes: {ausentes}" if ausentes else ", ".join(esperados)))

    mal_formados, com_ns_flex, imports_flex = [], [], []
    texto_total = ""
    for f in fontes:
        texto = f.read_text(encoding="utf-8")
        texto_total += texto + "\n"
        rel = f.relative_to(src_royale).as_posix()
        if f.suffix == ".mxml":
            try:
                ET.fromstring(texto.encode("utf-8"))
            except ET.ParseError as exc:
                mal_formados.append(f"{rel}: {exc}")
            for ns in (NS_MX, NS_SPARK, NS_MX_2006):
                if ns in texto:
                    com_ns_flex.append(f"{rel}: {ns}")
        for imp in RE_IMPORT.findall(texto):
            if imp.startswith(("mx.", "spark.", "flash.")):
                imports_flex.append(f"{rel}: {imp}")

    v.append(Validacao("MXML bem formado (XML válido)", not mal_formados, "; ".join(mal_formados)))
    v.append(Validacao("Nenhum namespace Flex (mx/spark) no código Royale", not com_ns_flex, "; ".join(com_ns_flex)))
    v.append(Validacao("Nenhum import mx.*, spark.* ou flash.*", not imports_flex, "; ".join(imports_flex)))

    arq_principal = src_royale / principal
    if arq_principal.is_file():
        t = arq_principal.read_text(encoding="utf-8")
        raiz_ok = bool(re.search(r"<(j|js):Application\b", t))
        v.append(Validacao("Arquivo principal usa j:Application (Royale)", raiz_ok))
        v.append(Validacao("Application declara SimpleCSSValuesImpl", "SimpleCSSValuesImpl" in t,
                           severidade="aviso"))
        if re.search(r'="\{[^"]+\}"', t):
            tem_bead = "DataBinding" in t
            v.append(Validacao("Bindings têm bead de DataBinding", tem_bead, severidade="aviso",
                               detalhe="" if tem_bead else "use <js:ApplicationDataBinding/> na Application"))

    # layout: Card com altura fixa corta o formulário (os campos ficam invisíveis, sem rolagem)
    cortes = []
    for f in fontes:
        if f.suffix == ".mxml":
            cortes += [f"{f.relative_to(src_royale).as_posix()}: {m}" for m in cards_com_form_e_altura(f)]
    v.append(Validacao("Nenhum j:Card com height fixo contendo j:Form", not cortes, severidade="aviso",
                       detalhe=("remova o height do Card (o formulário fica cortado): " + "; ".join(cortes))
                       if cortes else ""))

    # contrato da API preservado
    for url in inventario["urls_api"]:
        chave = url.rstrip("/")
        v.append(Validacao(f"Endpoint '{chave}' presente no código Royale", chave in texto_total))
    for parametro in ("suppress_response_codes", "_method"):
        if any(parametro in (Path(inventario["projeto"]) / "src" / a["caminho"]).read_text(encoding="utf-8")
               for a in inventario["arquivos"]):
            v.append(Validacao(f"Parâmetro de contrato '{parametro}' preservado", parametro in texto_total))

    # rastreabilidade das funções
    funcoes_origem = set()
    for a in inventario["arquivos"]:
        funcoes_origem.update(a["analise"].get("funcoes", []))
    funcoes_destino = set(RE_FUNCAO.findall(texto_total))
    perdidas = sorted(funcoes_origem - funcoes_destino)
    v.append(Validacao("Funções da origem preservadas no destino", not perdidas, severidade="aviso",
                       detalhe=(f"ausentes: {perdidas}" if perdidas else f"{len(funcoes_origem)} função(ões)")))
    return v


# ---------------------------------------------------------------------- pacote HTML5

def validar_pacote(destino: Path, principal: str) -> List[Validacao]:
    nome = Path(principal).stem
    www = destino / "www"
    v: List[Validacao] = []
    index = www / "index.html"
    v.append(Validacao("www/index.html gerado", index.is_file()))
    if index.is_file():
        html = index.read_text(encoding="utf-8")
        v.append(Validacao(f"index.html carrega {nome}.js", f"{nome}.js" in html))
        v.append(Validacao("index.html não depende de Flash/SWF", ".swf" not in html.lower()
                           and "shockwave" not in html.lower()))
    js = www / f"{nome}.js"
    v.append(Validacao(f"{nome}.js gerado", js.is_file(), f"{js.stat().st_size} bytes" if js.is_file() else ""))
    css = list(www.glob("*.css"))
    v.append(Validacao("CSS gerado", bool(css), ", ".join(c.name for c in css)))
    nginx = destino / "nginx.conf"
    v.append(Validacao("nginx.conf encaminha /api para o backend Java 7",
                       nginx.is_file() and "location /api/" in nginx.read_text(encoding="utf-8")))
    for arq in ("Dockerfile", "docker-compose.yml", "README.md", "src/" + principal):
        v.append(Validacao(f"{arq} presente", (destino / arq).is_file()))
    return v


def cards_com_form_e_altura(arquivo: Path) -> List[str]:
    """Encontra j:Card com atributo height que contêm um j:Form (padrão que corta o formulário)."""
    try:
        raiz = ET.fromstring(arquivo.read_text(encoding="utf-8").encode("utf-8"))
    except ET.ParseError:
        return []
    ns_jewel = "{library://ns.apache.org/royale/jewel}"
    achados = []
    for card in raiz.iter(ns_jewel + "Card"):
        if card.get("height") and any(True for _ in card.iter(ns_jewel + "Form")):
            achados.append(f'j:Card height="{card.get("height")}"')
    return achados
