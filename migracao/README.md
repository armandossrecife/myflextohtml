# Pipeline de migração Adobe Flex → HTML5 (Claude Platform + Apache Royale)

Esta ferramenta migra telas **Adobe Flex** (MXML + ActionScript 3) para **HTML5, CSS e JavaScript** com:

- **dois agentes da Claude Platform** (Messages API com *tool use*, modelo padrão `claude-sonnet-5`);
- o **compilador Apache Royale 0.9.12**, que roda **dentro do container da aplicação Flex** (estágio
  `migrador` do `frontend/Dockerfile`, que herda o Flex SDK, o JDK e o código-fonte Flex).

O exemplo de migração é a tela da agenda (`frontend/src`). O resultado é um segundo projeto,
`../agenda-contatos-html5`, que usa **a mesma API Java 7** sem nenhuma mudança no backend.

```
 ┌──────────────── container "migrador" (FROM build do Flex) ────────────────────────────────┐
 │                                                                                            │
 │  frontend/src (MXML/AS3) ──► 01 preparação ──► 02 baseline Flex (mxmlc Flex SDK → SWF)      │
 │                                   │                                                        │
 │                                   ▼                                                        │
 │                     03 análise ── Agente Analista Flex (Claude) ─ lê o código e registra   │
 │                                   │                                componentes, lógica,    │
 │                                   ▼                                API, riscos e plano     │
 │                     04 conversão ─ Agente Analista Flex (Claude) ─ passa o código para     │
 │                                   │                                MXML/AS3 Royale (Jewel) │
 │                                   ▼                                                        │
 │                     05 compilação ─ mxmlc Apache Royale ◄──► Agente Assistente do          │
 │                                   │   (HTML5/CSS/JS)          Compilador (Claude): corrige │
 │                                   ▼                           erros e recompila            │
 │                     06 empacotamento (www/, nginx /api → backend:8080, Docker)             │
 │                                   ▼                                                        │
 │                     07 integração: HTML5 servido + chamadas reais à API Java 7 ────────────┼──► backend (Tomcat 7 / Java 7)
 │                                   ▼                                                        │
 │                     relatório + logs (execucoes/<id>/ e agenda-contatos-html5/logs-migracao)│
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Como executar

Pré-requisitos: o projeto `agenda-contatos` rodando (`docker compose up -d`) e uma chave da
Claude Platform (console.anthropic.com → API Keys).

```bash
cd ~/Documents/agenda-contatos

# 1. chave da Claude Platform (e, se quiser, outro modelo)
export ANTHROPIC_API_KEY=sk-ant-...
# export CLAUDE_MODEL=claude-sonnet-5          # padrão

# 2. constrói o container migrador (Flex SDK + Royale + SDK anthropic). Leva alguns minutos na 1ª vez.
docker compose --profile migracao build migrador

# 3. executa o pipeline completo e gera ../agenda-contatos-html5
docker compose --profile migracao run --rm migrador

# 4. sobe a aplicação HTML5 migrada (porta 8082), que usa a mesma API Java 7
cd ../agenda-contatos-html5
docker compose up -d --build
open http://localhost:8082          # Flex original continua em http://localhost:8080

# 5. (opcional) teste E2E no navegador (Chromium headless) da tela migrada
cd ../agenda-contatos
docker compose --profile migracao run --rm e2e
```

### Ensaio sem API (modo simulado)

Para conferir a infraestrutura (container, Royale, validações, logs) sem gastar tokens:

```bash
docker compose --profile migracao run --rm -e MODO_MIGRACAO=simulado migrador
```

No modo simulado os "agentes" seguem um roteiro fixo e gravam a conversão de referência
(`referencia/src`, feita e testada à mão), com um erro de compilação injetado de propósito para
exercitar o laço do Agente Assistente do Compilador. **Não é uma migração feita por IA.**

### Opções do `migrar.py`

| Opção | Padrão | Descrição |
|---|---|---|
| `--origem` | `../frontend` | projeto Flex (pasta com `src/`) |
| `--destino` | `../../agenda-contatos-html5` | projeto HTML5 gerado |
| `--principal` | `Agenda.mxml` | MXML principal |
| `--modelo` | `claude-sonnet-5` (`$CLAUDE_MODEL`) | modelo da Claude Platform |
| `--modo` | `claude` (`$MODO_MIGRACAO`) | `claude` ou `simulado` |
| `--tentativas` | `5` | máximo de compilações do Royale na etapa 05 |
| `--pensamento` | `0` | orçamento de *extended thinking* por turno (0 = desligado) |
| `--api-teste` | `http://backend:8080/api` | API Java 7 do teste de integração |
| `--pular-integracao` | — | não executa a etapa 07 |
| `--verbose` | — | mostra também os eventos DEBUG |

Exemplo com argumentos: `docker compose --profile migracao run --rm migrador python migrar.py --origem /workspace/agenda-contatos/frontend --destino /workspace/agenda-contatos-html5 --tentativas 8 --verbose`

## Etapas e validações

Cada etapa só roda se a anterior passou em todas as validações **bloqueantes**. As de nível **aviso**
são registradas, mas não interrompem o pipeline.

| # | Etapa | O que faz | Principais validações |
|---|---|---|---|
| 01 | preparação | confere Java 8 (Flex), Java 17 (Royale), Royale, Flex SDK e chave da API; inventário estático (arquivos, SHA-256, componentes, endpoints) | projeto Flex existe, Royale instalado, Java 11+ para o Royale, chave configurada |
| 02 | baseline-flex | compila o Flex original com o `mxmlc` do Flex SDK | a origem compila e gera o SWF |
| 03 | análise | **Agente Analista** lê MXML/AS3 e o guia e chama `registrar_analise` | todo arquivo no plano, todo componente `mx:` mapeado, endpoints identificados, arquivo principal preservado |
| 04 | conversão | **Agente Analista** grava o código Royale (`escrever_arquivo`) e chama `concluir_conversao` | MXML bem formado, sem namespaces nem imports `mx`/`spark`/`flash`, `j:Application`, endpoints e parâmetros do contrato preservados, funções da origem presentes, **nenhum `j:Card` com `height` fixo contendo `j:Form`** (aviso de layout devolvido uma vez ao agente para correção) |
| 05 | compilação | `mxmlc` do Royale → HTML5/JS/CSS. Se falhar, o **Agente Assistente do Compilador** lê os erros, corrige e recompila (`compilar_royale`) até o limite | 0 erros, `index.html` + JS + CSS gerados, tentativas dentro do limite |
| 06 | empacotamento | `www/`, `nginx.conf` (proxy `/api` → `backend:8080`), `Dockerfile`, `docker-compose.yml` na rede do projeto Flex | arquivos presentes, `index.html` carrega o JS e não usa SWF, proxy da API configurado |
| 07 | integração | serve o `www/` e faz, pelo mesmo `/api`, as chamadas que a tela faz (listar, criar, `_method=PUT`, validação, `_method=DELETE`) | API Java 7 UP, CRUD completo com o contrato do Flex, JS gerado contém o contrato |
| — | relatório | sempre executa: `relatorio-migracao.md`, `resumo.json`, `README.md` do projeto HTML5 | — |

Os agentes também passam por validação **durante** o trabalho. Se a análise ou a conversão não passar
nos validadores estáticos, a ferramenta de conclusão é recusada e o agente recebe a lista do que falta
corrigir.

O teste E2E (`docker compose --profile migracao run --rm e2e`) confere no navegador: carga sem SWF, lista,
seleção, **todos os campos do formulário visíveis (nenhum cortado por container com overflow)**, criação
e exclusão pela tela, e ausência de erros de JavaScript.

## Histórico de versões

- **1.1**
  - O validador da análise aceita componentes agrupados ou anotados (ex.: `"mx:DataGrid + mx:DataGridColumn"`, `"mx:Button label="`).
  - O Agente Analista usa o mesmo conjunto de ferramentas na análise e na conversão, o que mantém o
    *prompt caching* entre as duas tarefas. As ferramentas usadas fora da tarefa certa são recusadas com uma mensagem.
  - O guia ganhou a regra de layout "sem `height` fixo em `j:Card` com `j:Form`", com validação estática.
  - O E2E ganhou um passo que confere se algum campo do formulário ficou cortado.
- **1.0**: versão inicial.

## Logs

Cada execução cria `migracao/execucoes/AAAAMMDD-HHMMSS/`, que também é copiada para
`agenda-contatos-html5/logs-migracao/`:

| Arquivo | Conteúdo |
|---|---|
| `pipeline.log` | log legível: `data [nível] [etapa] ação: mensagem` |
| `eventos.jsonl` | os mesmos eventos em JSON (ts, decorrido, nível, etapa, ação, mensagem, detalhes) |
| `etapas/NN-nome.json` | status, duração, resultado e validações de cada etapa |
| `agentes/<agente>/turno-NN.json` | cada chamada à API: modelo, `stop_reason`, tokens, latência e resposta completa |
| `compilacao/tentativa-NN.log` | comando e saída completa do compilador Royale |
| `inventario-flex.json` | inventário estático do código Flex |
| `analise-agente.json` / `conversao-agente.json` | o que cada agente registrou ao concluir |
| `integracao-evidencias.json` | requisições e respostas do teste de integração |
| `relatorio-migracao.md` / `resumo.json` | relatório final |
| `e2e-*/` | resultado do teste E2E (log, JSON e capturas de tela), quando executado |

Principais ações registradas: `etapa.inicio/fim`, `validacao`, `agente.inicio/resposta/ferramenta/fim`,
`ferramenta.ler/escrever/substituir`, `royale.compilar/resultado`, `compilacao.correcao`,
`conversao.decisao/pendencia`, `integracao.chamada`, `pipeline.fim`.

## Estrutura

```
migracao/
├── migrar.py                    CLI do pipeline
├── pipeline/
│   ├── etapas.py                infraestrutura: Config, Contexto, Validacao, execução sequencial
│   ├── estagios.py              as 7 etapas e a configuração dos dois agentes
│   ├── agentes.py               laço agêntico sobre a Messages API (streaming, tool use, cache, logs)
│   ├── ferramentas.py           ferramentas dos agentes com acesso restrito (flex/ leitura, royale/ escrita, guia/ leitura)
│   ├── royale.py                execução dos compiladores Royale e Flex e leitura dos diagnósticos
│   ├── inventario.py            análise estática de MXML/AS3
│   ├── validacoes.py            validadores de análise, código Royale e pacote HTML5
│   ├── integracao.py            teste de integração com a API Java 7
│   ├── relatorio.py             relatório e README do projeto HTML5
│   ├── registro.py              logs (pipeline.log, eventos.jsonl, artefatos)
│   └── simulado.py              cliente falso da API para o modo simulado
├── prompts/                     system prompts dos dois agentes
├── conhecimento/
│   ├── guia-royale-jewel.md     base de conhecimento Flex → Royale (padrões testados, erros comuns)
│   └── index-template.html      template HTML5 usado pelo compilador
├── templates/html5/             Dockerfile, nginx.conf e docker-compose.yml do projeto gerado
├── referencia/src/              conversão manual de referência (usada só no modo simulado)
├── e2e/teste-e2e.mjs            teste de navegador (Playwright)
└── execucoes/                   logs das execuções
```

## Custos e limites

- Os dois agentes usam *prompt caching* automático. O system prompt e o guia são reaproveitados entre turnos.
- O uso de tokens por agente aparece no relatório e em cada `turno-NN.json`.
- A qualidade da conversão depende do modelo e do guia. Os validadores e o teste de integração pegam
  regressões de contrato, mas **revise a tela migrada** (layout e fluxos) antes de usar em produção.
