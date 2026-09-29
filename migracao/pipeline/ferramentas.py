"""Ferramentas (tools) que os agentes podem chamar, com acesso restrito a pastas.

Os caminhos usam prefixos lógicos, assim o agente nunca vê caminhos reais do container:

* ``flex/...``    código-fonte Flex original   (somente leitura)
* ``royale/...``  código-fonte Royale gerado   (leitura e escrita)
* ``guia/...``    base de conhecimento Royale  (somente leitura)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .registro import Registro

LIMITE_LEITURA = 200_000  # caracteres


class ErroFerramenta(Exception):
    pass


class SistemaArquivos:
    def __init__(self, raizes: Dict[str, Path], gravaveis: List[str], reg: Registro, agente: str):
        self.raizes = {k: v.resolve() for k, v in raizes.items()}
        self.gravaveis = set(gravaveis)
        self.reg = reg
        self.agente = agente
        self.escritos: List[str] = []

    def _resolver(self, caminho_logico: str, escrita: bool = False) -> Path:
        caminho_logico = caminho_logico.strip().lstrip("/")
        prefixo, _, resto = caminho_logico.partition("/")
        if prefixo not in self.raizes:
            raise ErroFerramenta(f"Prefixo inválido '{prefixo}'. Use um de: {', '.join(p + '/' for p in self.raizes)}")
        if escrita and prefixo not in self.gravaveis:
            raise ErroFerramenta(f"'{prefixo}/' é somente leitura")
        raiz = self.raizes[prefixo]
        destino = (raiz / resto).resolve()
        if destino != raiz and raiz not in destino.parents:
            raise ErroFerramenta("Caminho fora da área permitida")
        return destino

    def listar(self, caminho: str = "") -> str:
        if not caminho:
            return "\n".join(f"{p}/" for p in self.raizes)
        base = self._resolver(caminho)
        if not base.exists():
            raise ErroFerramenta(f"Não existe: {caminho}")
        prefixo = caminho.strip("/").split("/")[0]
        itens = []
        for p in sorted(base.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.raizes[prefixo]).as_posix()
                itens.append(f"{prefixo}/{rel}  ({p.stat().st_size} bytes)")
        return "\n".join(itens) or "(vazio)"

    def ler(self, caminho: str) -> str:
        arq = self._resolver(caminho)
        if not arq.is_file():
            raise ErroFerramenta(f"Arquivo não encontrado: {caminho}")
        texto = arq.read_text(encoding="utf-8", errors="replace")
        self.reg.debug("ferramenta.ler", f"{self.agente} leu {caminho} ({len(texto)} caracteres)")
        if len(texto) > LIMITE_LEITURA:
            return texto[:LIMITE_LEITURA] + "\n...[truncado]"
        return texto

    def escrever(self, caminho: str, conteudo: str) -> str:
        arq = self._resolver(caminho, escrita=True)
        arq.parent.mkdir(parents=True, exist_ok=True)
        existia = arq.exists()
        arq.write_text(conteudo, encoding="utf-8")
        if caminho not in self.escritos:
            self.escritos.append(caminho)
        self.reg.info("ferramenta.escrever",
                      f"{self.agente} {'atualizou' if existia else 'criou'} {caminho} "
                      f"({conteudo.count(chr(10)) + 1} linhas)")
        return f"OK: {caminho} {'atualizado' if existia else 'criado'} ({len(conteudo)} caracteres)"

    def substituir(self, caminho: str, trecho_antigo: str, trecho_novo: str) -> str:
        arq = self._resolver(caminho, escrita=True)
        if not arq.is_file():
            raise ErroFerramenta(f"Arquivo não encontrado: {caminho}")
        texto = arq.read_text(encoding="utf-8")
        ocorrencias = texto.count(trecho_antigo)
        if ocorrencias != 1:
            raise ErroFerramenta(f"O trecho antigo aparece {ocorrencias} vezes; ele deve ser único")
        arq.write_text(texto.replace(trecho_antigo, trecho_novo), encoding="utf-8")
        if caminho not in self.escritos:
            self.escritos.append(caminho)
        self.reg.info("ferramenta.substituir", f"{self.agente} editou {caminho}")
        return f"OK: trecho substituído em {caminho}"


# ---------------------------------------------------------------------- definições para a API

def definicao(nome: str, descricao: str, propriedades: Dict[str, Any], obrigatorias: List[str]) -> Dict[str, Any]:
    return {
        "name": nome,
        "description": descricao,
        "input_schema": {"type": "object", "properties": propriedades, "required": obrigatorias},
    }


FERRAMENTA_LISTAR = definicao(
    "listar_arquivos",
    "Lista os arquivos de uma área (flex/, royale/ ou guia/). Sem caminho, lista as áreas disponíveis.",
    {"caminho": {"type": "string", "description": "Ex.: 'flex/', 'royale/src/'"}}, [])

FERRAMENTA_LER = definicao(
    "ler_arquivo",
    "Lê um arquivo de texto completo. Ex.: 'flex/Agenda.mxml', 'guia/guia-royale-jewel.md'.",
    {"caminho": {"type": "string"}}, ["caminho"])

FERRAMENTA_ESCREVER = definicao(
    "escrever_arquivo",
    "Cria ou sobrescreve um arquivo na área royale/ com o conteúdo completo. Ex.: 'royale/src/Agenda.mxml'.",
    {"caminho": {"type": "string"}, "conteudo": {"type": "string", "description": "Conteúdo completo do arquivo"}},
    ["caminho", "conteudo"])

FERRAMENTA_SUBSTITUIR = definicao(
    "substituir_trecho",
    "Substitui um trecho único de um arquivo em royale/ (use para correções pequenas).",
    {"caminho": {"type": "string"}, "trecho_antigo": {"type": "string"}, "trecho_novo": {"type": "string"}},
    ["caminho", "trecho_antigo", "trecho_novo"])


def executores_basicos(fs: SistemaArquivos) -> Dict[str, Callable[[Dict[str, Any]], str]]:
    return {
        "listar_arquivos": lambda a: fs.listar(a.get("caminho", "")),
        "ler_arquivo": lambda a: fs.ler(a["caminho"]),
        "escrever_arquivo": lambda a: fs.escrever(a["caminho"], a["conteudo"]),
        "substituir_trecho": lambda a: fs.substituir(a["caminho"], a["trecho_antigo"], a["trecho_novo"]),
    }


def resumo_argumentos(argumentos: Dict[str, Any], limite: int = 160) -> str:
    """Resumo curto dos argumentos de uma chamada, para o log (sem despejar arquivos inteiros)."""
    partes = []
    for chave, valor in argumentos.items():
        if isinstance(valor, str) and len(valor) > limite:
            partes.append(f"{chave}=<{len(valor)} caracteres>")
        elif isinstance(valor, (dict, list)):
            texto = json.dumps(valor, ensure_ascii=False)
            partes.append(f"{chave}=<json {len(texto)} caracteres>" if len(texto) > limite else f"{chave}={texto}")
        else:
            partes.append(f"{chave}={valor!r}")
    return ", ".join(partes)


def executar_ferramenta(executores: Dict[str, Callable[[Dict[str, Any]], str]], nome: str,
                        argumentos: Dict[str, Any]) -> tuple:
    """Executa a ferramenta e devolve (texto_resultado, is_error)."""
    funcao: Optional[Callable[[Dict[str, Any]], str]] = executores.get(nome)
    if funcao is None:
        return f"Ferramenta desconhecida: {nome}", True
    try:
        return str(funcao(argumentos)), False
    except (ErroFerramenta, KeyError, ValueError) as exc:
        return f"Erro: {exc}", True
