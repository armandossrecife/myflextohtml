"""Infraestrutura de etapas: contexto compartilhado, validações e execução sequencial."""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .registro import Registro


@dataclass
class Validacao:
    nome: str
    ok: bool
    detalhe: str = ""
    # "bloqueante": se falhar, o pipeline para. "aviso": registrada, mas não interrompe.
    severidade: str = "bloqueante"

    def como_dict(self) -> Dict[str, Any]:
        return {"nome": self.nome, "ok": self.ok, "severidade": self.severidade, "detalhe": self.detalhe}


@dataclass
class Config:
    origem: Path                 # projeto Flex (pasta que contém src/)
    destino: Path                # projeto HTML5 a ser gerado
    execucao: Path               # pasta de logs desta execução
    modelo: str = "claude-sonnet-5"
    modo: str = "claude"         # "claude" (API real) ou "simulado" (sem API, usa a referência)
    max_tentativas_compilacao: int = 5
    flex_home: Optional[Path] = None
    royale_home: Optional[Path] = None
    java_royale: Optional[Path] = None   # JAVA_HOME usado pelo Royale (Java 11+)
    api_base_teste: str = "http://backend:8080/api"
    arquivo_principal: str = "Agenda.mxml"
    pular_integracao: bool = False
    pensamento_tokens: int = 0            # >0 ativa extended thinking nos agentes


@dataclass
class Contexto:
    config: Config
    reg: Registro
    dados: Dict[str, Any] = field(default_factory=dict)       # resultados compartilhados entre etapas
    uso_tokens: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def somar_tokens(self, agente: str, uso: Dict[str, int]) -> None:
        total = self.uso_tokens.setdefault(agente, {})
        for chave, valor in uso.items():
            if isinstance(valor, int):
                total[chave] = total.get(chave, 0) + valor


class Etapa:
    numero: int = 0
    nome: str = ""
    titulo: str = ""
    descricao: str = ""

    def executar(self, ctx: Contexto) -> Dict[str, Any]:  # pragma: no cover - abstrato
        raise NotImplementedError

    def validar(self, ctx: Contexto, resultado: Dict[str, Any]) -> List[Validacao]:
        return []

    @property
    def rotulo(self) -> str:
        return f"{self.numero:02d}-{self.nome}"


@dataclass
class ResultadoEtapa:
    etapa: str
    titulo: str
    status: str                      # "sucesso" | "falhou" | "erro" | "pulada"
    duracao_s: float
    validacoes: List[Validacao]
    resultado: Dict[str, Any]
    erro: str = ""

    def como_dict(self) -> Dict[str, Any]:
        return {
            "etapa": self.etapa,
            "titulo": self.titulo,
            "status": self.status,
            "duracao_s": round(self.duracao_s, 2),
            "validacoes": [v.como_dict() for v in self.validacoes],
            "resultado": self.resultado,
            "erro": self.erro,
        }


def executar_pipeline(ctx: Contexto, etapas: List[Etapa],
                      ao_terminar: Optional[Callable[[List[ResultadoEtapa]], None]] = None) -> List[ResultadoEtapa]:
    reg = ctx.reg
    resultados: List[ResultadoEtapa] = []
    interromper = False

    for etapa in etapas:
        reg.etapa_atual = etapa.rotulo
        if interromper:
            resultados.append(ResultadoEtapa(etapa.rotulo, etapa.titulo, "pulada", 0.0, [], {}))
            reg.aviso("etapa.pulada", f"{etapa.titulo} não executada (etapa anterior falhou)")
            continue

        reg.info("etapa.inicio", f"{etapa.titulo} - {etapa.descricao}")
        inicio = time.time()
        resultado: Dict[str, Any] = {}
        validacoes: List[Validacao] = []
        erro = ""
        try:
            resultado = etapa.executar(ctx) or {}
            validacoes = etapa.validar(ctx, resultado)
        except Exception as exc:  # erro inesperado na etapa
            erro = f"{type(exc).__name__}: {exc}"
            reg.erro("etapa.excecao", erro, traceback=traceback.format_exc())
        duracao = time.time() - inicio

        for v in validacoes:
            if v.ok:
                reg.ok("validacao", f"{v.nome}" + (f" - {v.detalhe}" if v.detalhe else ""))
            elif v.severidade == "aviso":
                reg.aviso("validacao", f"{v.nome} - {v.detalhe}")
            else:
                reg.erro("validacao", f"{v.nome} - {v.detalhe}")

        bloqueio = any((not v.ok) and v.severidade == "bloqueante" for v in validacoes)
        status = "erro" if erro else ("falhou" if bloqueio else "sucesso")
        item = ResultadoEtapa(etapa.rotulo, etapa.titulo, status, duracao, validacoes, resultado, erro)
        resultados.append(item)
        reg.salvar_json(f"etapas/{etapa.rotulo}.json", item.como_dict())

        if status == "sucesso":
            aprovadas = sum(1 for v in validacoes if v.ok)
            reg.ok("etapa.fim", f"{etapa.titulo} concluída em {duracao:.1f}s "
                                f"({aprovadas}/{len(validacoes)} validações aprovadas)")
        else:
            reg.erro("etapa.fim", f"{etapa.titulo} terminou com status '{status}' em {duracao:.1f}s")
            interromper = True

    reg.etapa_atual = "fim"
    if ao_terminar:
        ao_terminar(resultados)
    return resultados
