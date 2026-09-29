"""Modo simulado: um cliente falso que imita a Messages API.

Serve para testar o pipeline inteiro (ferramentas, laço agêntico, validações, compilador Royale,
empacotamento, logs) sem chave de API e sem custo. As "respostas" seguem um roteiro fixo:

* Agente Analista: lê os arquivos, registra uma análise montada a partir do inventário estático e
  grava a conversão de referência (``referencia/src``), de propósito com um erro típico de migração
  (``enabled`` num botão Jewel);
* Agente Assistente do Compilador: lê o arquivo, corrige o erro, recompila e conclui.

Não é uma migração feita por IA. É só um ensaio técnico do pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REFERENCIA = Path(__file__).resolve().parent.parent / "referencia" / "src"
ERRO_INJETADO_DE = '<j:Button text="Salvar" emphasis="primary" click="salvar()"/>'
ERRO_INJETADO_PARA = '<j:Button text="Salvar" emphasis="primary" click="salvar()" enabled="{!ocupado}"/>'
CARD_OK = '<j:Card width="45%">'
CARD_CORTADO = '<j:Card width="45%" height="600">'

MAPA = {
    "mx:Application": "j:Application + j:initialView/j:View", "mx:HBox": "j:HGroup",
    "mx:HDividedBox": "j:HGroup", "mx:Panel": "j:Card (CardHeader + CardPrimaryContent)",
    "mx:ControlBar": "j:CardActions", "mx:DataGrid": "j:DataGrid", "mx:DataGridColumn": "j:DataGridColumn",
    "mx:columns": "j:columns", "mx:Form": "j:Form", "mx:FormItem": "j:FormItem",
    "mx:FormHeading": "j:FormHeading", "mx:Label": "j:Label", "mx:TextInput": "j:TextInput",
    "mx:Button": "j:Button", "mx:List": "j:List", "mx:Spacer": "j:Spacer",
}


class _Fluxo:
    def __init__(self, resposta: Dict[str, Any]):
        self.resposta = resposta

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self) -> Dict[str, Any]:
        return self.resposta


class _Mensagens:
    def __init__(self):
        self.contador = 0

    def stream(self, **params: Any) -> _Fluxo:
        self.contador += 1
        return _Fluxo(_roteiro(params, self.contador))


class ClienteSimulado:
    simulado = True

    def __init__(self):
        self.messages = _Mensagens()


def _uso(entrada: int, saida: int) -> Dict[str, int]:
    return {"input_tokens": entrada, "output_tokens": saida,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


def _ferramenta(n: int, nome: str, entrada: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_sim_{n:04d}_{nome}", "name": nome, "input": entrada}


def _resposta(blocos: List[Dict[str, Any]], motivo: str = "tool_use") -> Dict[str, Any]:
    return {"content": blocos, "stop_reason": motivo, "usage": _uso(1200, 400)}


def _passo_atual(mensagens: List[Dict[str, Any]]) -> tuple:
    """Devolve (índice da tarefa atual, nº de respostas do assistente desde a tarefa, texto da tarefa)."""
    inicio = max(i for i, m in enumerate(mensagens) if m["role"] == "user" and isinstance(m["content"], str))
    passos = sum(1 for m in mensagens[inicio:] if m["role"] == "assistant")
    return inicio, passos, mensagens[inicio]["content"]


def _ultimo_resultado(mensagens: List[Dict[str, Any]]) -> str:
    ultimo = mensagens[-1]
    if isinstance(ultimo["content"], list):
        return " ".join(str(b.get("content", "")) for b in ultimo["content"] if isinstance(b, dict))
    return str(ultimo["content"])


def _analise(tarefa: str) -> Dict[str, Any]:
    inventario = json.loads(tarefa[tarefa.index("{"):])
    arquivos = [{"origem": a, "destino": f"royale/src/{a}",
                 "papel": "tela principal" if a.endswith(".mxml") else "cliente da API REST"}
                for a in inventario["arquivos"]]
    return {
        "resumo": "Agenda de contatos (CRUD) em Flex MX: DataGrid com a lista, formulário com nome, telefones, "
                  "e-mails e endereço; comunicação REST/JSON com a API Java 7 por HTTPService. (modo simulado)",
        "arquivos": arquivos,
        # como o modelo real costuma fazer: alguns componentes agrupados/anotados numa só entrada
        "componentes": [{"flex": c, "royale": MAPA.get(c, "ver guia"), "observacao": ""}
                        for c in inventario["componentes_flex"]
                        if c not in ("mx:DataGrid", "mx:DataGridColumn", "mx:columns", "mx:Button")]
                       + [{"flex": "mx:DataGrid + mx:DataGridColumn + mx:columns", "royale": "j:DataGrid"},
                          {"flex": "mx:Button label=", "royale": "j:Button text="}],
        "servicos": [
            {"operacao": "listar/buscar", "metodo_http": "GET", "url": "/contatos?q=",
             "contrato": "suppress_response_codes=true, _ts"},
            {"operacao": "buscar por id", "metodo_http": "GET", "url": "/contatos/{id}", "contrato": ""},
            {"operacao": "criar", "metodo_http": "POST", "url": "/contatos", "contrato": "JSON do contato"},
            {"operacao": "atualizar", "metodo_http": "POST (_method=PUT)", "url": "/contatos/{id}", "contrato": ""},
            {"operacao": "excluir", "metodo_http": "POST (_method=DELETE)", "url": "/contatos/{id}",
             "contrato": "corpo {}"},
        ],
        "logica": [{"nome": "salvar", "descricao": "valida e cria/atualiza"},
                   {"nome": "carregar", "descricao": "lista com filtro"}],
        "bindings": ["contatos", "telefones", "emails", "idAtual", "ocupado"],
        "riscos": [{"descricao": "enabled não existe no Jewel", "mitigacao": "validar no handler"},
                   {"descricao": "Alert.yesLabel estático não existe", "mitigacao": "AlertModel"}],
        "plano_conversao": ["esqueleto j:Application", "ApiClient com org.apache.royale.net.HTTPService",
                            "tela com Card/Form/DataGrid"],
    }


def _roteiro(params: Dict[str, Any], n: int) -> Dict[str, Any]:
    ferramentas = {t["name"] for t in params.get("tools", [])}
    mensagens = params["messages"]
    _, passo, tarefa = _passo_atual(mensagens)

    if "TAREFA 1" in tarefa and "registrar_analise" in ferramentas:   # Agente Analista - análise
        if passo == 0:
            return _resposta([{"type": "text", "text": "Vou ler o código Flex."},
                              _ferramenta(n, "listar_arquivos", {"caminho": "flex/"}),
                              _ferramenta(n + 1, "ler_arquivo", {"caminho": "flex/Agenda.mxml"}),
                              _ferramenta(n + 2, "ler_arquivo", {"caminho": "flex/br/ufpi/agenda/ApiClient.as"})])
        return _resposta([_ferramenta(n, "registrar_analise", _analise(tarefa))])

    if "TAREFA 2" in tarefa and "concluir_conversao" in ferramentas:  # Agente Analista - conversão
        arquivos = sorted(p for p in REFERENCIA.rglob("*") if p.is_file())
        if passo < len(arquivos):
            arq = arquivos[passo]
            conteudo = arq.read_text(encoding="utf-8")
            if arq.name == "Agenda.mxml":
                # dois erros típicos: 'enabled' (quebra a compilação) e Card do formulário com height
                # fixo (compila, mas corta os campos; o validador de layout devolve para correção)
                conteudo = conteudo.replace(ERRO_INJETADO_DE, ERRO_INJETADO_PARA)
                conteudo = conteudo.replace(CARD_OK, CARD_CORTADO)
            rel = arq.relative_to(REFERENCIA).as_posix()
            return _resposta([_ferramenta(n, "escrever_arquivo", {"caminho": f"royale/src/{rel}", "conteudo": conteudo})])
        if "recusada" in _ultimo_resultado(mensagens) and "j:Card" in _ultimo_resultado(mensagens):
            return _resposta([{"type": "text", "text": "O Card do formulário não pode ter height fixo; removo."},
                              _ferramenta(n, "substituir_trecho", {"caminho": "royale/src/Agenda.mxml",
                                                                   "trecho_antigo": CARD_CORTADO,
                                                                   "trecho_novo": CARD_OK})])
        return _resposta([_ferramenta(n, "concluir_conversao", {
            "resumo": "Conversão de referência gravada (modo simulado).",
            "arquivos": [f"royale/src/{p.relative_to(REFERENCIA).as_posix()}" for p in arquivos],
            "decisoes": ["mx:Panel -> j:Card", "mx:HTTPService -> org.apache.royale.net.HTTPService"],
            "pendencias": ["HDividedBox sem divisor arrastável no Jewel"]})])

    if "concluir_compilacao" in ferramentas:                    # Agente Assistente do Compilador
        if passo == 0:
            return _resposta([_ferramenta(n, "ler_arquivo", {"caminho": "royale/src/Agenda.mxml"})])
        if passo == 1:
            return _resposta([{"type": "text", "text": "O Jewel não tem 'enabled'; removo o atributo."},
                              _ferramenta(n, "substituir_trecho", {"caminho": "royale/src/Agenda.mxml",
                                                                   "trecho_antigo": ERRO_INJETADO_PARA,
                                                                   "trecho_novo": ERRO_INJETADO_DE})])
        if passo == 2:
            return _resposta([_ferramenta(n, "compilar_royale", {})])
        ok = "Compilação OK" in _ultimo_resultado(mensagens)
        return _resposta([_ferramenta(n, "concluir_compilacao", {
            "resumo": "Removido atributo inexistente no Jewel.", "compilou": ok,
            "correcoes": [{"arquivo": "royale/src/Agenda.mxml",
                           "erro": "This attribute is unexpected (enabled)",
                           "correcao": "removido enabled do botão Salvar; o handler já checa 'ocupado'"}]})])

    return _resposta([{"type": "text", "text": "(roteiro simulado sem passo para esta tarefa)"}], "end_turn")
