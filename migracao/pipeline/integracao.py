"""Teste de integração da aplicação HTML5 gerada com a API Java 7 real.

Sobe um servidor HTTP local que faz o mesmo papel do nginx da aplicação migrada (arquivos
estáticos de www/ e /api encaminhado ao backend) e executa as mesmas chamadas que o código
Royale faz, no mesmo formato. Assim fica provado que a nova aplicação fala com a API sem mudanças.
"""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .etapas import Validacao


class _Handler(SimpleHTTPRequestHandler):
    api_base = ""

    def log_message(self, *args):  # silencioso: o pipeline registra o que importa
        pass

    def _proxy(self, metodo: str) -> None:
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho) if tamanho else None
        destino = self.api_base.rstrip("/") + self.path[len("/api"):]
        req = urllib.request.Request(destino, data=corpo, method=metodo)
        if self.headers.get("Content-Type"):
            req.add_header("Content-Type", self.headers["Content-Type"])
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status, dados, tipo = resp.status, resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            status, dados, tipo = exc.code, exc.read(), exc.headers.get("Content-Type", "")
        except Exception as exc:  # backend fora do ar
            status, dados, tipo = 502, json.dumps({"erro": str(exc)}).encode(), "application/json"
        self.send_response(status)
        self.send_header("Content-Type", tipo or "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy("GET")
        return super().do_GET()

    def do_POST(self):
        self._proxy("POST")


def _http(url: str, metodo: str = "GET", corpo: Any = None) -> Tuple[int, str]:
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    if dados is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:
        return 0, str(exc)


def testar(www: Path, principal: str, api_base: str, reg) -> Tuple[List[Validacao], Dict[str, Any]]:
    nome = Path(principal).stem
    handler = partial(type("H", (_Handler,), {"api_base": api_base}), directory=str(www))
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{porta}"
    reg.info("integracao.servidor", f"Servidor local em {base} (/api -> {api_base})")
    v: List[Validacao] = []
    evidencias: Dict[str, Any] = {"base": base, "api": api_base, "chamadas": []}

    def chamada(descricao: str, metodo: str, caminho: str, corpo: Any = None) -> Tuple[int, Any]:
        status, texto = _http(base + caminho, metodo, corpo)
        try:
            dados = json.loads(texto)
        except ValueError:
            dados = texto[:300]
        evidencias["chamadas"].append({"descricao": descricao, "metodo": metodo, "url": caminho,
                                       "status": status, "resposta": dados if len(texto) < 2000 else "(grande)"})
        reg.info("integracao.chamada", f"{descricao}: {metodo} {caminho} -> HTTP {status}")
        return status, dados

    try:
        # 1) arquivos estáticos
        status, html = _http(base + "/")
        v.append(Validacao("index.html servido (HTTP 200)", status == 200))
        for arq in re.findall(r'(?:src|href)="\.?/?([^"]+\.(?:js|css))"', html if status == 200 else ""):
            if arq.startswith("http"):
                continue
            st, _ = _http(f"{base}/{arq}")
            v.append(Validacao(f"{arq} servido (HTTP 200)", st == 200))
        js = (www / f"{nome}.js").read_text(encoding="utf-8", errors="replace") if (www / f"{nome}.js").is_file() else ""
        for trecho in ("contatos", "suppress_response_codes", "_method"):
            v.append(Validacao(f"JavaScript gerado contém '{trecho}' (mesmo contrato do Flex)", trecho in js))

        # 2) API Java 7 alcançável pelo mesmo caminho /api usado pela aplicação
        status, saude = chamada("health", "GET", "/api/health")
        backend_ok = status == 200 and isinstance(saude, dict) and saude.get("status") == "UP"
        v.append(Validacao("API Java 7 acessível via /api (health UP)", backend_ok,
                           json.dumps(saude, ensure_ascii=False)[:200]))
        if backend_ok:
            v.append(Validacao("Backend roda em Java 7", str(saude.get("java", "")).startswith("1.7"),
                               severidade="aviso", detalhe=str(saude.get("java"))))
        if not backend_ok:
            return v, evidencias

        # 3) mesmas chamadas que o ApiClient Royale faz
        q = "suppress_response_codes=true&_ts=1"
        status, lista = chamada("listar", "GET", f"/api/contatos?{q}")
        v.append(Validacao("Listar contatos (GET /api/contatos)", status == 200 and isinstance(lista, list),
                           f"{len(lista) if isinstance(lista, list) else 0} contato(s)"))
        novo = {"id": None, "nome": "Teste Pipeline Migração", "telefones": ["(86) 3000-0000"],
                "emails": ["pipeline@teste.com"],
                "endereco": {"rua": "Rua do Teste, 1", "cep": "64000-000", "cidade": "Teresina",
                             "estado": "PI", "pais": "Brasil"}}
        status, criado = chamada("criar", "POST", f"/api/contatos?{q}", novo)
        criado_ok = status == 200 and isinstance(criado, dict) and isinstance(criado.get("id"), int)
        v.append(Validacao("Criar contato (POST)", criado_ok))
        if criado_ok:
            cid = criado["id"]
            novo["nome"] = "Teste Pipeline Migração (editado)"
            status, editado = chamada("atualizar", "POST", f"/api/contatos/{cid}?{q}&_method=PUT", novo)
            v.append(Validacao("Atualizar contato (POST + _method=PUT)",
                               status == 200 and isinstance(editado, dict) and editado.get("nome") == novo["nome"]))
            status, erro = chamada("validação", "POST", f"/api/contatos?{q}", {"nome": " "})
            v.append(Validacao("Erro de validação chega como JSON com 'erro'",
                               status == 200 and isinstance(erro, dict) and "erro" in erro))
            status, excl = chamada("excluir", "POST", f"/api/contatos/{cid}?{q}&_method=DELETE", {})
            v.append(Validacao("Excluir contato (POST + _method=DELETE)",
                               status == 200 and isinstance(excl, dict) and excl.get("excluido") == cid))
    finally:
        servidor.shutdown()
    return v, evidencias
