"""Agentes da migração, implementados sobre a API da Claude Platform (Messages API + tool use).

Cada agente roda um laço agêntico manual:

    1. envia system prompt + histórico + ferramentas para o modelo;
    2. executa as ferramentas pedidas (ler/escrever arquivos, compilar...);
    3. devolve os resultados e repete, até o agente chamar a sua ferramenta de conclusão.

Todas as chamadas são registradas em ``agentes/<agente>/turno-NN.json`` (requisição resumida,
resposta completa, uso de tokens) e os principais eventos vão para o log do pipeline.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .etapas import Contexto
from .ferramentas import executar_ferramenta, resumo_argumentos

MAX_TOKENS_PADRAO = 32000


def _campo(bloco: Any, nome: str, padrao: Any = None) -> Any:
    if isinstance(bloco, dict):
        return bloco.get(nome, padrao)
    return getattr(bloco, nome, padrao)


def _serializar(bloco: Any) -> Dict[str, Any]:
    if isinstance(bloco, dict):
        return bloco
    if hasattr(bloco, "model_dump"):
        return bloco.model_dump(exclude_none=True)
    return {"repr": repr(bloco)}


def _uso(resposta: Any) -> Dict[str, int]:
    uso = _campo(resposta, "usage")
    if uso is None:
        return {}
    dados = uso if isinstance(uso, dict) else (uso.model_dump() if hasattr(uso, "model_dump") else vars(uso))
    return {k: v for k, v in dados.items() if isinstance(v, int)}


def criar_cliente(modo: str):
    """Cria o cliente da API. No modo 'simulado' quem responde é um roteiro local (ver simulado.py)."""
    if modo == "simulado":
        from .simulado import ClienteSimulado
        return ClienteSimulado()
    import anthropic  # importado aqui para o modo simulado funcionar mesmo sem o SDK
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Defina a variável ANTHROPIC_API_KEY (chave da Claude Platform)")
    return anthropic.Anthropic(max_retries=4, timeout=900)


@dataclass
class ResultadoAgente:
    concluido: bool
    ferramenta_final: Optional[str]
    dados_finais: Dict[str, Any]
    turnos: int
    chamadas_ferramentas: int
    uso_tokens: Dict[str, int]
    texto_final: str = ""
    duracao_s: float = 0.0


@dataclass
class Agente:
    nome: str                                   # ex.: "analista-flex"
    papel: str                                  # descrição curta para o log
    system: List[Dict[str, Any]]                # blocos de system prompt
    ferramentas: List[Dict[str, Any]]           # definições (JSON schema) enviadas à API
    executores: Dict[str, Callable[[Dict[str, Any]], str]]
    ferramentas_finais: List[str]               # chamar uma delas encerra o laço
    max_turnos: int = 40
    max_tokens: int = MAX_TOKENS_PADRAO
    pensamento_tokens: int = 0                  # >0 ativa extended thinking com esse orçamento
    # ferramentas declaradas, mas que não valem na tarefa atual -> mensagem de erro devolvida ao agente
    ferramentas_fora_de_fase: Dict[str, str] = field(default_factory=dict)
    historico: List[Dict[str, Any]] = field(default_factory=list)

    def executar(self, ctx: Contexto, cliente: Any, tarefa: str,
                 validar_final: Optional[Callable[[str, Dict[str, Any]], Optional[str]]] = None) -> ResultadoAgente:
        """Roda o laço agêntico para uma tarefa. ``validar_final`` pode recusar a conclusão (devolvendo
        uma mensagem de erro que é repassada ao agente para ele corrigir)."""
        reg = ctx.reg
        modelo = ctx.config.modelo
        pasta = f"agentes/{self.nome}"
        self.historico.append({"role": "user", "content": tarefa})
        inicio = time.time()
        uso_total: Dict[str, int] = {}
        chamadas = 0
        cobrancas_sem_ferramenta = 0
        texto_final = ""

        reg.info("agente.inicio", f"{self.nome} ({self.papel}) iniciou a tarefa com o modelo {modelo}")

        for turno in range(1, self.max_turnos + 1):
            parametros: Dict[str, Any] = dict(
                model=modelo,
                max_tokens=self.max_tokens,
                system=self.system,
                tools=self.ferramentas,
                messages=self.historico,
            )
            if self.pensamento_tokens > 0:
                parametros["thinking"] = {"type": "enabled", "budget_tokens": self.pensamento_tokens}
            if not getattr(cliente, "simulado", False):
                parametros["cache_control"] = {"type": "ephemeral"}   # cache automático do prefixo

            t0 = time.time()
            with cliente.messages.stream(**parametros) as fluxo:
                resposta = fluxo.get_final_message()
            latencia = time.time() - t0

            conteudo = list(_campo(resposta, "content", []))
            motivo = _campo(resposta, "stop_reason")
            uso = _uso(resposta)
            for k, v in uso.items():
                uso_total[k] = uso_total.get(k, 0) + v
            ctx.somar_tokens(self.nome, uso)

            reg.salvar_json(f"{pasta}/turno-{len(list((ctx.reg.pasta / pasta).glob('turno-*.json'))) + 1:02d}.json", {
                "agente": self.nome, "turno": turno, "modelo": modelo, "stop_reason": motivo,
                "latencia_s": round(latencia, 2), "uso": uso,
                "ultima_mensagem_enviada": _resumir_mensagem(self.historico[-1]),
                "resposta": [_serializar(b) for b in conteudo],
            })
            reg.info("agente.resposta",
                     f"{self.nome} turno {turno}: stop_reason={motivo}, "
                     f"tokens entrada={uso.get('input_tokens', 0)} saída={uso.get('output_tokens', 0)} "
                     f"cache_lido={uso.get('cache_read_input_tokens', 0)}, {latencia:.1f}s")

            for bloco in conteudo:
                if _campo(bloco, "type") == "text" and _campo(bloco, "text", "").strip():
                    texto_final = _campo(bloco, "text")
                    reg.debug("agente.texto", f"{self.nome}: {texto_final[:600]}")

            if motivo == "max_tokens":
                # a resposta foi cortada: descarta e pede para dividir o trabalho
                reg.aviso("agente.max_tokens", f"{self.nome}: resposta cortada por max_tokens; pedindo para dividir")
                self.historico.append({"role": "assistant", "content": [{"type": "text", "text": "(resposta cortada)"}]})
                self.historico.append({"role": "user", "content":
                    "Sua última resposta foi cortada por excesso de tamanho e foi descartada. "
                    "Refaça em partes menores: escreva um arquivo por chamada e seja mais conciso no texto."})
                continue
            if motivo == "refusal":
                reg.erro("agente.recusa", f"{self.nome} recusou a tarefa")
                break

            self.historico.append({"role": "assistant", "content": conteudo})
            usos_ferramenta = [b for b in conteudo if _campo(b, "type") == "tool_use"]

            if not usos_ferramenta:
                cobrancas_sem_ferramenta += 1
                if cobrancas_sem_ferramenta > 2:
                    reg.erro("agente.sem_conclusao", f"{self.nome} parou sem chamar {self.ferramentas_finais}")
                    break
                self.historico.append({"role": "user", "content":
                    f"Continue a tarefa usando as ferramentas. Quando terminar, chame "
                    f"{' ou '.join(self.ferramentas_finais)}."})
                continue

            resultados = []
            final: Optional[tuple] = None
            for uso_f in usos_ferramenta:
                nome = _campo(uso_f, "name")
                argumentos = _campo(uso_f, "input") or {}
                chamadas += 1
                reg.info("agente.ferramenta", f"{self.nome} -> {nome}({resumo_argumentos(argumentos)})")
                if nome in self.ferramentas_finais:
                    recusa = validar_final(nome, argumentos) if validar_final else None
                    if recusa:
                        reg.aviso("agente.conclusao_recusada", f"{self.nome}: {recusa[:300]}")
                        resultados.append({"type": "tool_result", "tool_use_id": _campo(uso_f, "id"),
                                           "content": recusa, "is_error": True})
                    else:
                        resultados.append({"type": "tool_result", "tool_use_id": _campo(uso_f, "id"),
                                           "content": "Conclusão registrada. Obrigado."})
                        final = (nome, argumentos)
                    continue
                if nome in self.ferramentas_fora_de_fase:
                    reg.aviso("agente.ferramenta_fora_de_fase", f"{self.nome} chamou {nome} fora da tarefa certa")
                    resultados.append({"type": "tool_result", "tool_use_id": _campo(uso_f, "id"),
                                       "content": self.ferramentas_fora_de_fase[nome], "is_error": True})
                    continue
                texto, erro = executar_ferramenta(self.executores, nome, argumentos)
                if erro:
                    reg.aviso("agente.ferramenta_erro", f"{self.nome} -> {nome}: {texto[:300]}")
                resultados.append({"type": "tool_result", "tool_use_id": _campo(uso_f, "id"),
                                   "content": texto, "is_error": erro})
            self.historico.append({"role": "user", "content": resultados})

            if final:
                duracao = time.time() - inicio
                reg.ok("agente.fim", f"{self.nome} concluiu com {final[0]} após {turno} turno(s), "
                                     f"{chamadas} chamada(s) de ferramenta, {duracao:.1f}s")
                return ResultadoAgente(True, final[0], final[1], turno, chamadas, uso_total, texto_final, duracao)

        duracao = time.time() - inicio
        reg.erro("agente.fim", f"{self.nome} não concluiu a tarefa ({chamadas} chamadas, {duracao:.1f}s)")
        return ResultadoAgente(False, None, {}, self.max_turnos, chamadas, uso_total, texto_final, duracao)


def _resumir_mensagem(msg: Dict[str, Any]) -> Any:
    conteudo = msg.get("content")
    if isinstance(conteudo, str):
        return {"role": msg["role"], "texto": conteudo[:4000]}
    itens = []
    for b in conteudo or []:
        b = _serializar(b)
        if b.get("type") == "tool_result":
            texto = b.get("content")
            texto = texto if isinstance(texto, str) else json.dumps(texto, ensure_ascii=False)
            itens.append({"tool_result": b.get("tool_use_id"), "is_error": b.get("is_error", False),
                          "conteudo": texto[:2000]})
        else:
            itens.append(b)
    return {"role": msg["role"], "itens": itens}


def carregar_prompt(pasta: Path, nome: str, **variaveis: str) -> str:
    texto = (pasta / nome).read_text(encoding="utf-8")
    for chave, valor in variaveis.items():
        texto = texto.replace("{{" + chave + "}}", valor)
    return texto
