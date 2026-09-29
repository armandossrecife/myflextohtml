"""Registro (log) da execução do pipeline.

Cada execução grava em ``execucoes/<id>/``:

* ``pipeline.log``   - log legível, uma linha por evento
* ``eventos.jsonl``  - o mesmo evento em JSON (uma linha por evento), para análise automática
* ``etapas/NN-<nome>.json`` - resultado e validações de cada etapa
* ``agentes/``       - transcrições das conversas com os agentes (requisições, respostas, tokens)
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_NIVEIS = {"DEBUG": 10, "INFO": 20, "OK": 25, "AVISO": 30, "ERRO": 40}
_CORES = {"DEBUG": "\033[90m", "INFO": "\033[0m", "OK": "\033[32m", "AVISO": "\033[33m", "ERRO": "\033[31m"}


class Registro:
    def __init__(self, pasta: Path, nivel_console: str = "INFO"):
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)
        (self.pasta / "etapas").mkdir(exist_ok=True)
        (self.pasta / "agentes").mkdir(exist_ok=True)
        self._log = open(self.pasta / "pipeline.log", "a", encoding="utf-8")
        self._jsonl = open(self.pasta / "eventos.jsonl", "a", encoding="utf-8")
        self._lock = threading.Lock()
        self._nivel_console = _NIVEIS[nivel_console]
        self.etapa_atual = "-"
        self.inicio = time.time()

    # ------------------------------------------------------------------ eventos
    def evento(self, nivel: str, acao: str, mensagem: str, **detalhes: Any) -> None:
        agora = datetime.now(timezone.utc).astimezone()
        registro = {
            "ts": agora.isoformat(timespec="milliseconds"),
            "decorrido_s": round(time.time() - self.inicio, 2),
            "nivel": nivel,
            "etapa": self.etapa_atual,
            "acao": acao,
            "mensagem": mensagem,
        }
        if detalhes:
            registro["detalhes"] = detalhes
        linha = f"{agora:%Y-%m-%d %H:%M:%S} [{nivel:<5}] [{self.etapa_atual}] {acao}: {mensagem}"
        with self._lock:
            self._log.write(linha + "\n")
            self._log.flush()
            self._jsonl.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
            self._jsonl.flush()
            if _NIVEIS[nivel] >= self._nivel_console:
                cor = _CORES.get(nivel, "") if sys.stdout.isatty() else ""
                fim = "\033[0m" if cor else ""
                print(f"{cor}{linha}{fim}", flush=True)

    def debug(self, acao: str, msg: str, **d: Any) -> None:
        self.evento("DEBUG", acao, msg, **d)

    def info(self, acao: str, msg: str, **d: Any) -> None:
        self.evento("INFO", acao, msg, **d)

    def ok(self, acao: str, msg: str, **d: Any) -> None:
        self.evento("OK", acao, msg, **d)

    def aviso(self, acao: str, msg: str, **d: Any) -> None:
        self.evento("AVISO", acao, msg, **d)

    def erro(self, acao: str, msg: str, **d: Any) -> None:
        self.evento("ERRO", acao, msg, **d)

    # ------------------------------------------------------------------ artefatos
    def salvar_json(self, relativo: str, dados: Any) -> Path:
        destino = self.pasta / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return destino

    def salvar_texto(self, relativo: str, texto: str) -> Path:
        destino = self.pasta / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        return destino

    def fechar(self) -> None:
        self._log.close()
        self._jsonl.close()
