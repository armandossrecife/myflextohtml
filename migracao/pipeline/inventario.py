"""Análise estática (determinística) do código Flex: MXML + ActionScript 3.

Serve para três coisas:
1. inventário da etapa de preparação (arquivos, hashes, tamanhos);
2. contexto extra para o Agente Analista;
3. "gabarito" para validar a análise do agente (ele não pode esquecer componentes ou endpoints).
"""
from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

NS_MX = "library://ns.adobe.com/flex/mx"
NS_SPARK = "library://ns.adobe.com/flex/spark"
NS_FX = "http://ns.adobe.com/mxml/2009"
NS_MX_2006 = "http://www.adobe.com/2006/mxml"
PREFIXOS = {NS_MX: "mx", NS_SPARK: "s", NS_FX: "fx", NS_MX_2006: "mx"}

RE_IMPORT = re.compile(r"^\s*import\s+([\w.*]+)\s*;", re.M)
RE_FUNCAO = re.compile(r"(?:public|private|protected|internal)?\s*(?:static\s+)?function\s+(?:get\s+|set\s+)?(\w+)\s*\(")
RE_URL = re.compile(r"[\"'](/[\w/{}.-]*contatos[\w/{}.-]*|/api[\w/{}.-]*)[\"']")
RE_HTTP = re.compile(r"\b(HTTPService|URLLoader|URLRequest|RemoteObject|WebService)\b")
RE_BINDING = re.compile(r"\{[^{}]+\}")


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def listar_fontes(src: Path) -> List[Path]:
    return sorted(p for p in src.rglob("*") if p.suffix in (".mxml", ".as") and p.is_file())


def _nome_tag(tag: str) -> str:
    if tag.startswith("{"):
        ns, local = tag[1:].split("}", 1)
        return f"{PREFIXOS.get(ns, ns)}:{local}"
    return tag


def analisar_mxml(caminho: Path) -> Dict[str, Any]:
    texto = caminho.read_text(encoding="utf-8")
    raiz = ET.fromstring(texto.encode("utf-8"))
    componentes: Dict[str, int] = {}
    ids: List[str] = []
    eventos: List[Dict[str, str]] = []
    bindings: List[str] = []
    atributos_evento = {"click", "change", "enter", "creationComplete", "initialize",
                        "applicationComplete", "itemClick", "close", "valueCommit", "focusOut"}
    for el in raiz.iter():
        nome = _nome_tag(el.tag)
        componentes[nome] = componentes.get(nome, 0) + 1
        if "id" in el.attrib:
            ids.append(el.attrib["id"])
        for attr, valor in el.attrib.items():
            if attr in atributos_evento:
                eventos.append({"componente": nome, "id": el.attrib.get("id", ""), "evento": attr, "handler": valor})
            for b in RE_BINDING.findall(valor):
                bindings.append(f"{nome}.{attr}={b}")

    scripts = "\n".join((s.text or "") for s in raiz.iter(f"{{{NS_FX}}}Script"))
    scripts += "\n".join((s.text or "") for s in raiz.iter(f"{{{NS_MX_2006}}}Script"))
    return {
        "arquivo": caminho.name,
        "raiz": _nome_tag(raiz.tag),
        "namespaces": sorted(set(re.findall(r'xmlns:(\w+)="([^"]+)"', texto))),
        "componentes": componentes,
        "ids": ids,
        "eventos": eventos,
        "bindings": bindings,
        "imports": RE_IMPORT.findall(scripts),
        "funcoes": sorted(set(RE_FUNCAO.findall(scripts))),
        "linhas": texto.count("\n") + 1,
    }


def analisar_as(caminho: Path) -> Dict[str, Any]:
    texto = caminho.read_text(encoding="utf-8")
    pacote = re.search(r"package\s+([\w.]*)", texto)
    classe = re.search(r"class\s+(\w+)", texto)
    return {
        "arquivo": caminho.name,
        "pacote": pacote.group(1) if pacote else "",
        "classe": classe.group(1) if classe else "",
        "imports": RE_IMPORT.findall(texto),
        "funcoes": sorted(set(RE_FUNCAO.findall(texto))),
        "servicos_rede": sorted(set(RE_HTTP.findall(texto))),
        "urls": sorted(set(RE_URL.findall(texto))),
        "linhas": texto.count("\n") + 1,
    }


def inventariar(projeto: Path) -> Dict[str, Any]:
    src = projeto / "src"
    arquivos = []
    componentes_total: Dict[str, int] = {}
    urls: set = set()
    for caminho in listar_fontes(src):
        rel = caminho.relative_to(src).as_posix()
        info: Dict[str, Any] = {"caminho": rel, "bytes": caminho.stat().st_size, "sha256": _sha256(caminho)}
        if caminho.suffix == ".mxml":
            info["tipo"] = "mxml"
            info["analise"] = analisar_mxml(caminho)
            for nome, qtd in info["analise"]["componentes"].items():
                componentes_total[nome] = componentes_total.get(nome, 0) + qtd
        else:
            info["tipo"] = "as3"
            info["analise"] = analisar_as(caminho)
            urls.update(info["analise"]["urls"])
        arquivos.append(info)

    componentes_visuais = sorted(n for n in componentes_total if n.startswith(("mx:", "s:")))
    return {
        "projeto": str(projeto),
        "arquivos": arquivos,
        "total_arquivos": len(arquivos),
        "total_linhas": sum(a["analise"]["linhas"] for a in arquivos),
        "componentes": componentes_total,
        "componentes_flex": componentes_visuais,
        "urls_api": sorted({u.rstrip("/") or "/" for u in urls}),
    }
