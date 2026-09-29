"""Execução dos compiladores: Apache Royale (MXML/AS3 -> HTML5/JS/CSS) e Apache Flex (baseline SWF)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

RE_DIAGNOSTICO = re.compile(
    r"^(?P<arquivo>/?[^\n()]+?\.(?:mxml|as|css))\((?P<linha>\d+)\): col: (?P<coluna>\d+) "
    r"(?P<tipo>Error|Warning): (?P<mensagem>.+)$", re.M)


@dataclass
class Diagnostico:
    arquivo: str
    linha: int
    coluna: int
    tipo: str
    mensagem: str
    trecho: str = ""

    def como_dict(self) -> Dict[str, object]:
        return self.__dict__.copy()

    def formatar(self) -> str:
        texto = f"{self.arquivo}({self.linha}) col {self.coluna} {self.tipo}: {self.mensagem}"
        return texto + (f"\n    {self.trecho}" if self.trecho else "")


@dataclass
class ResultadoCompilacao:
    sucesso: bool
    codigo_saida: int
    duracao_s: float
    comando: List[str]
    saida: str
    erros: List[Diagnostico] = field(default_factory=list)
    avisos: List[Diagnostico] = field(default_factory=list)
    artefatos: List[str] = field(default_factory=list)

    def resumo(self, maximo: int = 25) -> str:
        if self.sucesso:
            return (f"Compilação OK em {self.duracao_s:.1f}s, {len(self.avisos)} aviso(s). "
                    f"Artefatos: {', '.join(self.artefatos)}")
        linhas = [f"Compilação FALHOU (código {self.codigo_saida}) com {len(self.erros)} erro(s) "
                  f"e {len(self.avisos)} aviso(s):"]
        for d in (self.erros + self.avisos)[:maximo]:
            linhas.append("- " + d.formatar())
        if not self.erros:
            linhas.append("Saída do compilador (final):\n" + self.saida[-3000:])
        return "\n".join(linhas)


def _limpar_caminho(arquivo: str, raiz: Path) -> str:
    try:
        return Path(arquivo).resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return arquivo


def extrair_diagnosticos(saida: str, raiz: Path) -> List[Diagnostico]:
    diagnosticos = []
    linhas = saida.splitlines()
    indice = {linha: i for i, linha in enumerate(linhas)}
    for m in RE_DIAGNOSTICO.finditer(saida):
        trecho = ""
        i = indice.get(m.group(0))
        if i is not None:
            for proxima in linhas[i + 1:i + 4]:
                if proxima.strip() and proxima.strip() != "^":
                    trecho = proxima.strip()
                    break
        diagnosticos.append(Diagnostico(
            arquivo=_limpar_caminho(m.group("arquivo"), raiz), linha=int(m.group("linha")),
            coluna=int(m.group("coluna")), tipo=m.group("tipo"), mensagem=m.group("mensagem").strip(),
            trecho=trecho))
    return diagnosticos


def _executar(comando: List[str], cwd: Path, env: Dict[str, str], timeout: int) -> tuple:
    inicio = time.time()
    try:
        proc = subprocess.run(comando, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
        saida = proc.stdout + proc.stderr
        codigo = proc.returncode
    except subprocess.TimeoutExpired as exc:
        saida = f"{exc.stdout or ''}{exc.stderr or ''}\nTEMPO ESGOTADO após {timeout}s"
        codigo = -1
    saida = "\n".join(l for l in saida.splitlines() if not l.startswith("Picked up JAVA_TOOL_OPTIONS"))
    return codigo, saida, time.time() - inicio


def compilar_royale(royale_home: Path, projeto: Path, principal: str, java_home: Optional[Path] = None,
                    timeout: int = 600) -> ResultadoCompilacao:
    """Compila ``projeto/src/<principal>`` com o mxmlc do Royale (alvo JSRoyale) em ``projeto/bin``."""
    mxmlc = royale_home / "js" / "bin" / "mxmlc"
    tema = royale_home / "frameworks" / "themes" / "JewelTheme" / "src" / "main" / "resources" / "defaults.css"
    template = projeto / "template" / "index-template.html"
    comando = [
        str(mxmlc),
        "-targets=JSRoyale",
        f"-theme={tema}",
        "-source-path=src",
        f"-js-output={projeto}",
        "-js-dynamic-access-unknown-members=true",
        "-js-output-optimization=skipAsCoercions",
        "-remove-circulars",
    ]
    if template.is_file():
        comando.append(f"-html-template={template}")
    comando.append(f"src/{principal}")

    env = os.environ.copy()
    if java_home:
        env["JAVA_HOME"] = str(java_home)
        env["PATH"] = f"{java_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    release = projeto / "bin" / "js-release"
    if release.exists():
        shutil.rmtree(release)

    codigo, saida, duracao = _executar(comando, projeto, env, timeout)
    diagnosticos = extrair_diagnosticos(saida, projeto)
    erros = [d for d in diagnosticos if d.tipo == "Error"]
    avisos = [d for d in diagnosticos if d.tipo == "Warning"]
    artefatos = sorted(p.name for p in release.glob("*")) if release.exists() else []
    nome = Path(principal).stem
    sucesso = codigo == 0 and not erros and f"{nome}.js" in artefatos and "index.html" in artefatos
    return ResultadoCompilacao(sucesso, codigo, duracao, comando, saida, erros, avisos, artefatos)


def compilar_flex(flex_home: Path, projeto: Path, principal: str, saida_swf: Path,
                  timeout: int = 600) -> ResultadoCompilacao:
    """Compila o projeto Flex original (mesmos parâmetros do Dockerfile do frontend) para conferir a origem."""
    saida_swf.parent.mkdir(parents=True, exist_ok=True)
    comando = [
        "java", "-Xmx1024m", "-Djava.awt.headless=true", "-Dsun.io.useCanonCaches=false",
        "-jar", str(flex_home / "lib" / "mxmlc.jar"), f"+flexlib={flex_home / 'frameworks'}",
        "-source-path=src",
        f"-theme={flex_home / 'frameworks' / 'themes' / 'Halo' / 'halo.swc'}",
        "-target-player=11.1", "-swf-version=14",
        "-static-link-runtime-shared-libraries=true",
        "-debug=false",
        f"-output={saida_swf}",
        f"src/{principal}",
    ]
    codigo, saida, duracao = _executar(comando, projeto, os.environ.copy(), timeout)
    erros = [Diagnostico("", 0, 0, "Error", l.strip()) for l in saida.splitlines() if "Error:" in l]
    sucesso = codigo == 0 and saida_swf.is_file()
    artefatos = [f"{saida_swf.name} ({saida_swf.stat().st_size} bytes)"] if saida_swf.is_file() else []
    return ResultadoCompilacao(sucesso, codigo, duracao, comando, saida, erros, [], artefatos)
