# Processo de Migração de Telas de Aplicações Flex para Telas HTML5

Atualmente existe um sistema (backend) Java monolítico para prover serviços para uma aplicação (frontend) usando o Adobe Flex. Como a tecnologia do Adobe Flex foi descontinuada em 2011, existe uma necessidade de migrar esta aplicação para tecnologias de frontend que sejam executadas nos browsers modernos, utilizando por exemplo HTML5.

## Detalhes sobre o encerramento da tecnologia Adobe Flex

O Adobe Flex deixou de ser mantido diretamente pela Adobe em novembro de 2011, quando a empresa anunciou que encerraria o suporte comercial e doaria o código-fonte do Flex SDK para a Apache Software Foundation.

A partir de 2012, o projeto passou a se chamar Apache Flex, mantendo-se ativo de forma comunitária e aberta. No entanto, por depender essencialmente da plataforma Flash, o ecossistema como um todo sofreu o golpe final quando o Adobe Flash Player foi oficialmente descontinuado em 31 de dezembro de 2020 (com bloqueio total de execução em janeiro de 2021).

## Estudo de caso de uma aplicação modelo utilizando Java e Flex

Foi criada uma aplicação agenda-contatos (Agenda) - um CRUD simples de contatos - onde cada contato tem um id, nome, lista de telefones, lista de e-mails e endereço (rua, cep, cidade, estado, país), baseada em Java 7 (backend), Flex (frontend) e armazenamento de dados utilizando o MySQL 5.7. Para manter a independência de ambiente, compatibilidade em diferentes sistemas operacionais, foi adotada a abordagem de containers (Docker) para compor uma aplicação integrada via Docker compose. 

A aplicação tem três containers:

- **Frontend Flex**: Nginx servindo o Agenda.swf, com uma grade de contatos e um formulário. A comunicação com o backend é por REST/JSON via HTTPService.
- **Backend Java 7**: servlets no Tomcat 7 com JRE 7 real, gravando no banco com JDBC.
- **MySQL 5.7**: já vem com o esquema criado e 3 contatos de exemplo.

A aplicação está disponível em https://github.com/armandossrecife/agenda-contatos

Para executar esta aplicação, basta seguir as instruções do README.md do respectivo projeto. 

Para criar e executar a aplicação agenda-contatos original

```bash
docker compose up -d --build
```

O objetivo desta aplicação é servir de base para estudos relacionados a técnicas de migração, ou seja, esta aplicação é a aplicação origem (aplicação base). 

Como esta aplicação vai rodar em containers Dodker, a listagem dos containers ativos será algo como:

```bash
CONTAINER ID    IMAGE                 COMMAND                  CREATED          STATUS                    PORTS                               NAMES
?               agenda-frontend:1.0   "/docker-entrypoint.…"   12 minutes ago   Up 12 minutes             0.0.0.0:8080->80/tcp                agenda-frontend
?               agenda-backend:1.0    "catalina.sh run"        12 minutes ago   Up 12 minutes             0.0.0.0:8081->8080/tcp              agenda-backend
?               agenda-db:1.0         "docker-entrypoint.s…"   12 minutes ago   Up 12 minutes (healthy)   33060/tcp, 0.0.0.0:3307->3306/tcp   agenda-db
```

### Testar a API da aplicação

```bash
./testar-api.sh
````

Deverá mostrar algo como: 

```bash
armando@Mac agenda-contatos % ./testar-api.sh 

== Health check
{"java":"1.7.0_221","servidor":"Apache Tomcat/7.0.94","banco":"MySQL 5.7.44","status":"UP"}

== Listar contatos
[{"id":1,"nome":"Ana Beatriz Sousa","telefones":["(86) 3215-5500","(86) 99999-1234"],"emails":["ana.sousa@exemplo.com.br","ana@ufpi.edu.br"],"endereco":{"rua":"Av. Universitária, 1310","cep":"64049-550","cidade":"Teresina","estado":"PI","pais":"Brasil"}},{"id":2,"nome":"Carlos Eduardo Lima","telefones":["(85) 98888-4321"],"emails":["carlos.lima@exemplo.com.br"],"endereco":{"rua":"Rua das Flores, 45","cep":"60115-000","cidade":"Fortaleza","estado":"CE","pais":"Brasil"}},{"id":3,"nome":"María Fernández","telefones":["+507 6000-1111"],"emails":["maria.fernandez@ejemplo.com.pa"],"endereco":{"rua":"Calle 50, Edificio Sol","cep":"0801","cidade":"Ciudad de Panamá","estado":"Panamá","pais":"Panamá"}},{"id":6,"nome":"Maria Joaquina","telefones":["(86)994691234"],"emails":["maria.joaquina@gmail.com"],"endereco":{"rua":"Teste","cep":"64000","cidade":"Teresina","estado":"PI","pais":"Brasil"}}]

== Criar contato (POST)
{"id":7,"nome":"Teste via curl","telefones":["(86) 3000-0000","(86) 98888-0000"],"emails":["teste@exemplo.com"],"endereco":{"rua":"Rua A, 10","cep":"64000-000","cidade":"Teresina","estado":"PI","pais":"Brasil"}}

== Buscar contato 7 (GET)
{"id":7,"nome":"Teste via curl","telefones":["(86) 3000-0000","(86) 98888-0000"],"emails":["teste@exemplo.com"],"endereco":{"rua":"Rua A, 10","cep":"64000-000","cidade":"Teresina","estado":"PI","pais":"Brasil"}}

== Atualizar contato 7 (PUT)
{"id":7,"nome":"Teste via curl (editado)","telefones":["(86) 97777-0000"],"emails":["novo@exemplo.com","outro@exemplo.com"],"endereco":{"rua":"Rua B, 20","cep":"64000-111","cidade":"Parnaíba","estado":"PI","pais":"Brasil"}}

== Atualizar como o Flash faz (POST + _method=PUT + suppress_response_codes)
{"id":7,"nome":"Teste via Flash","telefones":[],"emails":[],"endereco":{"rua":null,"cep":null,"cidade":null,"estado":null,"pais":null}}

== Erro de validação (nome vazio) -> HTTP 400
{"erro":"O nome é obrigatório","status":400,"detalhes":["O nome é obrigatório"]}  [HTTP 400]

== Excluir contato 7 (DELETE)
{"excluido":7}

== Buscar contato excluído -> HTTP 404
{"erro":"Contato 7 não encontrado","status":404}  [HTTP 404]
```

### Abrir a aplicação Flex

Acesse **http://localhost:8080**.

Os navegadores atuais não têm mais o plugin Flash. Por isso, o `index.html` carrega o **[Ruffle](https://ruffle.rs)**, um emulador de Flash Player em WebAssembly, que executa o `Agenda.swf` direto na página. Com isso, é recomendável que você utilize o Google Chrome para testar a UI desta aplicação. 

Segue a Tela carregada, via Google Chrome (usando o Ruffle). Link da Tela1.

## Técnicas de Migração

Atualmente existem várias técnicas de migração de sistemas legados para tecnologias modernas, com isso, deverá ser feita uma revisão bibliográfica para identificar as principais técnicas, método e abordagens atuais, incluindo o uso de Modelos LLM. 

Enquanto isso, em um estudo preliminar adhoc, foi identificado o projeto [Apache Royale](https://royale.apache.org). 

O Apache Royale é um framework de software livre da Apache Software Foundation projetado para desenvolver aplicações web ricas (RIAs) de alta performance utilizando as linguagens ActionScript 3 e MXML. Ele é o sucessor direto do antigo Apache Flex.

Como ele funciona?

Diferente do Flex tradicional, que dependia do Adobe Flash Player ou do Adobe AIR para rodar, o Apache Royale funciona como um compilador.
- Você escreve o código em ActionScript 3 (lógica) e MXML (interface gráfica).
- O compilador do Royale traduz esse código diretamente para HTML, CSS e JavaScript.
- O resultado final roda nativamente em qualquer navegador moderno, sem a necessidade de plugins ou extensões.

### Abordagem inicial de migração

Uso do Apache Royale como um componente intermediário para traduzir um sistema original baseado em código Flex para um novo sistema utilizando HTML, CSS e javascript como frontend. 

**Detalhamento do Pipeline de migração**

O pipeline de migração está pronto na pasta `agenda-contatos/migracao`, é baseado em Agentes de IA Generativa para analisar o código do sistema original (sistema base), ele analisa o projeto frontend, e foi criada uma ferramenta em Python, que precisa de uma chave da Claude Platform. 

**Como o pipeline funciona**

- **Agente Analista Flex:** lê o MXML e o AS3, registra uma análise (componentes, lógica, chamadas à API, riscos, plano de arquivos) e depois reescreve o código para o Apache Royale.
- **Agente Assistente do Compilador:** roda o compilador do Royale, lê os erros, corrige o código e recompila, até um limite de tentativas.
- **Container:** o Royale 0.9.12 roda dentro do container da aplicação Flex. Foi criado um estágio `migrador` no `frontend/Dockerfile` que herda o Flex SDK e o código-fonte e acrescenta o Royale e um Java 17, porque o compilador do Royale exige Java 11 ou superior.
- **Etapas:**
  1. preparação do ambiente;
  2. compilação do Flex original, para confirmar que a origem compila;
  3. análise;
  4. conversão;
  5. compilação Royale com o agente corrigindo erros;
  6. empacotamento do projeto HTML5;
  7. teste de integração com a API Java 7;
  8. relatório final.
- **Validação por etapa:** cada etapa é validada antes da próxima começar. Se a análise ou a conversão do agente estiver incompleta, o pipeline recusa e devolve a lista do que falta.
- **Logs:** cada execução grava em `migracao/execucoes/<data-hora>/` o log legível, os eventos em JSON, cada chamada à API com os tokens gastos, a saída de cada compilação e o relatório. Uma cópia vai para dentro do projeto HTML5.
- **Mesma API Java 7:** a aplicação HTML5 roda em http://localhost:8082 e acessa o mesmo backend. O backend não mudou em nada.

**Testes usando a aplicação agenda-contatos**

- A tela da agenda foi convertida para o Royale como referência. Ela compilou e passou por criar, editar e excluir contatos num navegador real, incluindo a confirmação "Sim/Não".
- Foram executadas as 7 etapas do pipeline em modo simulado, com os agentes seguindo um roteiro fixo. Foi injetado um erro de compilação de propósito, e o laço do Agente Assistente corrigiu e recompilou.
- Foi executado o pipeline pelo SDK oficial da Anthropic contra um servidor que imita a API da Claude. Isso confirmou o streaming, as chamadas de ferramenta e o histórico da conversa.
- O teste de navegador (E2E) passou nos 7 passos contra o HTML5 gerado.

Nesses testes, a API usada foi uma imitação da API Java 7 feita por mim, e não o seu backend.

**Modelo:** o padrão é `claude-sonnet-5`. Esse ID aparece na documentação de IDs de modelo, mas a página de visão geral lista apenas o Claude Sonnet 5.5 (`claude-sonnet-5-5`) como modelo Sonnet atual. Se `claude-sonnet-5` der erro de modelo, troque com `export CLAUDE_MODEL=claude-sonnet-5-5`.

**Para executar**, no Terminal do Mac:

```bash
cd agenda-contatos
export ANTHROPIC_API_KEY=sk-ant-...
docker compose --profile migracao build migrador
docker compose --profile migracao run --rm migrador
```

Resultado do comando de migração: 

```bash
armando@Mac agenda-contatos % docker compose --profile migracao run --rm migrador
[+] Creating 2/2
 ✔ Container agenda-db       Running                                                                                                                                                                                                   0.0s 
 ✔ Container agenda-backend  Running                                                                                                                                                                                                   0.0s 
[+] Running 1/1
 ✔ Container agenda-db  Healthy                                                                                                                                                                                                        0.5s 
2026-09-29 15:56:14 [INFO ] [inicio] pipeline.inicio: Migração Flex -> HTML5 | modo=claude modelo=claude-sonnet-5
2026-09-29 15:56:14 [INFO ] [inicio] pipeline.config: origem=/workspace/agenda-contatos/frontend destino=/workspace/agenda-contatos-html5 logs=/workspace/agenda-contatos/migracao/execucoes/20260929-155614
2026-09-29 15:56:14 [INFO ] [01-preparacao] etapa.inicio: Preparação do ambiente - confere ferramentas (Flex SDK, Royale SDK, Java, API Claude) e inventaria o código Flex
2026-09-29 15:56:14 [INFO ] [01-preparacao] ambiente.java: Java padrão (Flex SDK): openjdk version "1.8.0_504"
2026-09-29 15:56:14 [INFO ] [01-preparacao] ambiente.java: Java do Royale: openjdk version "17.0.20.1" 2026-08-18
2026-09-29 15:56:14 [INFO ] [01-preparacao] inventario: 2 arquivo(s), 524 linhas, 16 tipos de componente Flex, endpoints: ['/contatos']
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Projeto Flex encontrado - /workspace/agenda-contatos/frontend/src/Agenda.mxml
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Código Flex inventariado - 2 arquivo(s)
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Apache Royale instalado no container - /opt/royale/node_modules/@apache-royale/royale-js/royale-asjs
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Java 11+ disponível para o Royale - openjdk version "17.0.20.1" 2026-08-18
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Apache Flex SDK instalado no container - /opt/flex
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: Chave da Claude Platform configurada - variável ANTHROPIC_API_KEY
2026-09-29 15:56:14 [OK   ] [01-preparacao] validacao: SDK anthropic instalado - 1.9.0
2026-09-29 15:56:14 [OK   ] [01-preparacao] etapa.fim: Preparação do ambiente concluída em 0.4s (7/7 validações aprovadas)
2026-09-29 15:56:14 [INFO ] [02-baseline-flex] etapa.inicio: Compilação de referência do Flex - compila o código Flex original com o Apache Flex SDK para garantir que a origem é válida
2026-09-29 15:56:14 [INFO ] [02-baseline-flex] flex.compilar: mxmlc (Flex SDK) em /workspace/agenda-contatos/frontend/src/Agenda.mxml
2026-09-29 15:56:15 [INFO ] [02-baseline-flex] flex.resultado: Compilação OK em 1.4s, 0 aviso(s). Artefatos: Agenda.swf (432283 bytes)
2026-09-29 15:56:15 [OK   ] [02-baseline-flex] validacao: Código Flex original compila (SWF gerado) - Agenda.swf (432283 bytes)
2026-09-29 15:56:15 [OK   ] [02-baseline-flex] etapa.fim: Compilação de referência do Flex concluída em 1.4s (1/1 validações aprovadas)
2026-09-29 15:56:15 [INFO ] [03-analise] etapa.inicio: Análise do código Flex (Agente Analista) - o agente lê MXML/AS3 e registra componentes, lógica, serviços, riscos e o plano de conversão
2026-09-29 15:56:15 [INFO ] [03-analise] agente.inicio: analista-flex (lê e analisa o código Flex e o converte para MXML/AS3 Royale) iniciou a tarefa com o modelo claude-sonnet-5
2026-09-29 15:56:18 [INFO ] [03-analise] agente.resposta: analista-flex turno 1: stop_reason=tool_use, tokens entrada=2 saída=143 cache_lido=0, 2.6s
2026-09-29 15:56:18 [INFO ] [03-analise] agente.ferramenta: analista-flex -> ler_arquivo(caminho='flex/Agenda.mxml')
2026-09-29 15:56:18 [INFO ] [03-analise] agente.ferramenta: analista-flex -> ler_arquivo(caminho='flex/br/ufpi/agenda/ApiClient.as')
2026-09-29 15:56:57 [INFO ] [03-analise] agente.resposta: analista-flex turno 2: stop_reason=tool_use, tokens entrada=2 saída=4870 cache_lido=9635, 39.2s
2026-09-29 15:56:57 [INFO ] [03-analise] agente.ferramenta: analista-flex -> registrar_analise(resumo=<517 caracteres>, arquivos=<json 309 caracteres>, componentes=<json 2075 caracteres>, servicos=<json 1134 caracteres>, logica=<json 2655 caracteres>, bindings=<json 357 caracteres>, riscos=<json 1507 caracteres>, plano_conversao=<json 1529 caracteres>)
2026-09-29 15:56:57 [OK   ] [03-analise] agente.fim: analista-flex concluiu com registrar_analise após 2 turno(s), 3 chamada(s) de ferramenta, 41.7s
2026-09-29 15:56:57 [INFO ] [03-analise] analise.resumo: Agenda de contatos: tela única em Flex/MX que lista contatos (grade com busca), permite criar/editar/excluir contatos com múltiplos telefones e e-mails e um endereço, via API REST/JSON (backend Java servido em /api). ApiClient encapsula chamadas HTTP com HTTPService usando GET/POST (com override _method=PUT|DELETE), suppress_response_codes=true e anti-cache _ts. A UI é dividida em painel de listagem (DataGrid) e painel de formulário (Form) lado a lado, com barra de busca no topo e barra de statu
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Agente analista concluiu a análise
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Todos os arquivos Flex estão no plano de conversão - 2 arquivo(s)
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Destinos apontam para royale/src/*.mxml|*.as - royale/src/Agenda.mxml, royale/src/br/ufpi/agenda/ApiClient.as
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Arquivo principal Agenda.mxml mantém o nome
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Todo componente Flex usado tem mapeamento para Royale - 15 componente(s)
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Endpoints da API identificados - 5 operação(ões)
2026-09-29 15:56:57 [OK   ] [03-analise] validacao: Riscos e decisões registrados - 8 risco(s)
2026-09-29 15:56:57 [OK   ] [03-analise] etapa.fim: Análise do código Flex (Agente Analista) concluída em 41.7s (7/7 validações aprovadas)
2026-09-29 15:56:57 [INFO ] [04-conversao] etapa.inicio: Conversão para MXML/AS3 Royale (Agente Analista) - o mesmo agente, com a análise em contexto, reescreve o código para Apache Royale / Jewel
2026-09-29 15:56:57 [INFO ] [04-conversao] agente.inicio: analista-flex (lê e analisa o código Flex e o converte para MXML/AS3 Royale) iniciou a tarefa com o modelo claude-sonnet-5
2026-09-29 15:57:54 [INFO ] [04-conversao] agente.resposta: analista-flex turno 1: stop_reason=tool_use, tokens entrada=2 saída=7224 cache_lido=17385, 57.4s
2026-09-29 15:57:54 [INFO ] [04-conversao] agente.ferramenta: analista-flex -> escrever_arquivo(caminho='royale/src/br/ufpi/agenda/ApiClient.as', conteudo=<4253 caracteres>)
2026-09-29 15:57:54 [INFO ] [04-conversao] ferramenta.escrever: analista-flex criou royale/src/br/ufpi/agenda/ApiClient.as (124 linhas)
2026-09-29 15:58:31 [INFO ] [04-conversao] agente.resposta: analista-flex turno 2: stop_reason=tool_use, tokens entrada=2 saída=5990 cache_lido=22774, 36.4s
2026-09-29 15:58:31 [INFO ] [04-conversao] agente.ferramenta: analista-flex -> escrever_arquivo(caminho='royale/src/Agenda.mxml', conteudo=<17542 caracteres>)
2026-09-29 15:58:31 [INFO ] [04-conversao] ferramenta.escrever: analista-flex criou royale/src/Agenda.mxml (430 linhas)
2026-09-29 15:58:44 [INFO ] [04-conversao] agente.resposta: analista-flex turno 3: stop_reason=tool_use, tokens entrada=2 saída=1289 cache_lido=30040, 12.6s
2026-09-29 15:58:44 [INFO ] [04-conversao] agente.ferramenta: analista-flex -> concluir_conversao(resumo=<856 caracteres>, arquivos=["royale/src/Agenda.mxml", "royale/src/br/ufpi/agenda/ApiClient.as"], decisoes=<json 1458 caracteres>, pendencias=<json 236 caracteres>)
2026-09-29 15:58:44 [OK   ] [04-conversao] agente.fim: analista-flex concluiu com concluir_conversao após 3 turno(s), 3 chamada(s) de ferramenta, 106.5s
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: Removido enabled='{}' dos botões (Buscar, Limpar busca, Limpar, Excluir, Salvar); a lógica de bloqueio por 'ocupado' e de contato selecionado passou para guarda (if) no início dos handlers carregar(), limparBusca(), salvar() e confirmarExclusao()
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: Removidos toolTip e maxChars de TextInput/Button (não suportados/erro no Jewel)
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: required='true' do FormItem 'Nome' virou asterisco no label ('Nome *')
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: grade.scrollToIndex removido de selecionarNaGrade (não existe no Jewel DataGrid); mantido apenas selectedIndex
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: FlexGlobals.topLevelApplication.parameters.apiUrl substituído por base fixa 'api', conforme guia
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: Colunas do DataGrid com labelFunction receberam dataField explícito (telefones/emails/endereco) pois o Jewel exige essa propriedade mesmo quando o valor exibido vem da função
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: Alert.yesLabel/noLabel estáticos substituídos por instância de Alert + AlertModel na confirmação de exclusão
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: Label de status do cabeçalho atualizado de 'Adobe Flex' para 'Apache Royale' para refletir a nova stack de frontend (mesmo texto descritivo, apenas o nome do framework)
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: TextInput e List dentro de FormItem/HGroup receberam largura fixa em pixels (320, 200, 280, 120) em vez de width=100%, conforme armadilha de layout do guia
2026-09-29 15:58:44 [INFO ] [04-conversao] conversao.decisao: HTTPService do ApiClient reescrito sem useProxy/resultFormat/requestTimeout/ResultEvent/FaultEvent, usando eventos COMPLETE/IO_ERROR e checagem de servico.status, mantendo idêntico o contrato de URLs e parâmetros
2026-09-29 15:58:44 [AVISO] [04-conversao] conversao.pendencia: setFocus() removido de txtNome/txtTelefone/txtEmail após ações (novo, adicionarTelefone, adicionarEmail, validação de salvar) por não haver equivalente no Jewel; o foco automático no campo não ocorre mais, apenas a limpeza/validação
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Agente concluiu a conversão
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Código Royale gerado - 2 arquivo(s)
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Todos os arquivos planejados foram gerados - Agenda.mxml, br/ufpi/agenda/ApiClient.as
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: MXML bem formado (XML válido)
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Nenhum namespace Flex (mx/spark) no código Royale
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Nenhum import mx.*, spark.* ou flash.*
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Arquivo principal usa j:Application (Royale)
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Application declara SimpleCSSValuesImpl
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Bindings têm bead de DataBinding
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Nenhum j:Card com height fixo contendo j:Form
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Endpoint '/contatos' presente no código Royale
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Parâmetro de contrato 'suppress_response_codes' preservado
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Parâmetro de contrato '_method' preservado
2026-09-29 15:58:44 [OK   ] [04-conversao] validacao: Funções da origem preservadas no destino - 30 função(ões)
2026-09-29 15:58:44 [OK   ] [04-conversao] etapa.fim: Conversão para MXML/AS3 Royale (Agente Analista) concluída em 106.5s (14/14 validações aprovadas)
2026-09-29 15:58:44 [INFO ] [05-compilacao] etapa.inicio: Compilação Royale assistida (Agente Assistente do Compilador) - o Royale traduz MXML/AS3 para HTML5/CSS/JS; o agente corrige o que o compilador rejeitar
2026-09-29 15:58:44 [INFO ] [05-compilacao] royale.compilar: tentativa 1 (pipeline)
2026-09-29 15:58:51 [OK   ] [05-compilacao] royale.resultado: Compilação OK em 7.8s, 0 aviso(s). Artefatos: Agenda.js, Agenda.min.css, index.html
2026-09-29 15:58:51 [OK   ] [05-compilacao] compilacao.direta: o código do Agente Analista compilou na primeira tentativa; o Agente Assistente do Compilador não foi necessário
2026-09-29 15:58:51 [OK   ] [05-compilacao] validacao: Royale compilou sem erros
2026-09-29 15:58:51 [OK   ] [05-compilacao] validacao: HTML5 gerado (index.html + JS + CSS) - Agenda.js, Agenda.min.css, index.html
2026-09-29 15:58:51 [OK   ] [05-compilacao] validacao: Compilações dentro do limite (5) - 1 tentativa(s)
2026-09-29 15:58:51 [OK   ] [05-compilacao] validacao: Sem avisos do compilador - 0 aviso(s)
2026-09-29 15:58:51 [OK   ] [05-compilacao] etapa.fim: Compilação Royale assistida (Agente Assistente do Compilador) concluída em 7.8s (4/4 validações aprovadas)
2026-09-29 15:58:51 [INFO ] [06-empacotamento] etapa.inicio: Empacotamento do projeto HTML5 - monta o projeto HTML5 (www/, nginx, Docker) apontando para a mesma API Java 7
2026-09-29 15:58:51 [INFO ] [06-empacotamento] pacote.www: 3 arquivo(s) copiados de bin/js-release para www/
2026-09-29 15:58:51 [INFO ] [06-empacotamento] pacote.arquivos: gerados: Dockerfile, nginx.conf, docker-compose.yml, .dockerignore
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: www/index.html gerado
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: index.html carrega Agenda.js
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: index.html não depende de Flash/SWF
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: Agenda.js gerado - 483797 bytes
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: CSS gerado - Agenda.min.css
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: nginx.conf encaminha /api para o backend Java 7
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: Dockerfile presente
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: docker-compose.yml presente
2026-09-29 15:58:51 [OK   ] [06-empacotamento] validacao: src/Agenda.mxml presente
2026-09-29 15:58:51 [OK   ] [06-empacotamento] etapa.fim: Empacotamento do projeto HTML5 concluída em 0.0s (9/9 validações aprovadas)
2026-09-29 15:58:51 [INFO ] [07-integracao] etapa.inicio: Teste de integração com a API Java 7 - serve o HTML5 gerado e executa, pelo mesmo /api, as chamadas que a tela faz
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.servidor: Servidor local em http://127.0.0.1:36487 (/api -> http://backend:8080/api)
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: health: GET /api/health -> HTTP 200
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: listar: GET /api/contatos?suppress_response_codes=true&_ts=1 -> HTTP 200
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: criar: POST /api/contatos?suppress_response_codes=true&_ts=1 -> HTTP 200
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: atualizar: POST /api/contatos/7?suppress_response_codes=true&_ts=1&_method=PUT -> HTTP 200
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: validação: POST /api/contatos?suppress_response_codes=true&_ts=1 -> HTTP 200
2026-09-29 15:58:51 [INFO ] [07-integracao] integracao.chamada: excluir: POST /api/contatos/7?suppress_response_codes=true&_ts=1&_method=DELETE -> HTTP 200
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: index.html servido (HTTP 200)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Agenda.min.css servido (HTTP 200)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Agenda.js servido (HTTP 200)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: JavaScript gerado contém 'contatos' (mesmo contrato do Flex)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: JavaScript gerado contém 'suppress_response_codes' (mesmo contrato do Flex)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: JavaScript gerado contém '_method' (mesmo contrato do Flex)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: API Java 7 acessível via /api (health UP) - {"java": "1.7.0_221", "servidor": "Apache Tomcat/7.0.94", "banco": "MySQL 5.7.44", "status": "UP"}
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Backend roda em Java 7 - 1.7.0_221
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Listar contatos (GET /api/contatos) - 4 contato(s)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Criar contato (POST)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Atualizar contato (POST + _method=PUT)
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Erro de validação chega como JSON com 'erro'
2026-09-29 15:58:52 [OK   ] [07-integracao] validacao: Excluir contato (POST + _method=DELETE)
2026-09-29 15:58:52 [OK   ] [07-integracao] etapa.fim: Teste de integração com a API Java 7 concluída em 0.6s (13/13 validações aprovadas)
2026-09-29 15:58:52 [OK   ] [fim] pipeline.fim: MIGRAÇÃO CONCLUÍDA | relatório: /workspace/agenda-contatos/migracao/execucoes/20260929-155614/relatorio-migracao.md
```

Em caso de sucesso "MIGRAÇÃO CONCLUÍDA", será gerada uma nova pasta **agenda-contatos-html5** (um nível acima) contendo a aplicação frontend migrada para HTML. Esta aplicação HTML migrada depende da aplicação API do mesmo backend da aplicação original. Observação: não é feita nenhuma alteração na aplicação backend, pois a migração só acontece na aplicação frontend. 

Para executar a aplicação UI em HTML em qualquer browser: 

No diretório **agenda-contatos-html5** no arquivo **docker-compose.yml** em networks: altere "name: agenda-contatos_default" para "name: myflextohtml_default"

```bash
cd ../agenda-contatos-html5 && docker compose up -d --build   # http://localhost:8082
```

Abra http://localhost:8082

O passo a passo completo está em `migracao/README.md`.