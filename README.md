# Agenda de Contatos: Adobe Flex + Java 7 + MySQL 5.7 (Docker)

Esta é uma aplicação CRUD de agenda de contatos na arquitetura clássica de sistemas Flex corporativos:

| Camada | Tecnologia | Container |
|---|---|---|
| Frontend | Adobe Flex (Apache Flex SDK 4.16.1, componentes MX/Halo), `HTTPService` + JSON | `agenda-frontend` (nginx) |
| Backend | Java 7, Servlet 3.0 no Tomcat 7, JDBC puro, Gson | `agenda-backend` (`tomcat:7-jre7`) |
| Banco | MySQL 5.7 | `agenda-db` (`mysql:5.7`) |

Cada contato tem `id`, `nome`, uma lista de telefones, uma lista de e-mails e um endereço (rua, CEP, cidade, estado, país).

```
Navegador ──► http://localhost:8080 (nginx)
                ├── /            index.html + Agenda.swf (Ruffle)
                └── /api/*  ───► backend:8080 (Tomcat 7 / Java 7) ───► db:3306 (MySQL 5.7)
```

---

## Passo a passo para executar

### 1. Pré-requisitos

- **Docker Desktop** (Windows/macOS) ou **Docker Engine + Compose v2** (Linux). Confira com:
  ```bash
  docker --version          # 20.10 ou superior
  docker compose version    # v2.x
  ```
- Acesso à internet no primeiro build, para baixar as imagens, as dependências do Maven, o Apache Flex SDK e o `playerglobal.swc`.
- Cerca de 3 GB livres em disco.
- As portas **8080**, **8081** e **3307** livres.

> **Macs com Apple Silicon (M1/M2/M3/M4):** as imagens `mysql:5.7` e `tomcat:7-jre7` só existem para amd64. O `docker-compose.yml` já declara `platform: linux/amd64`, e o Docker Desktop as executa por emulação (Rosetta). Se aparecer um erro de plataforma, ative em *Settings → General* a opção *Use Rosetta for x86_64/amd64 emulation on Apple Silicon*.

### 2. Obter o projeto

Descompacte o `agenda-contatos.zip` e entre na pasta:

```bash
unzip agenda-contatos.zip
cd agenda-contatos
```

### 3. Construir e subir os containers

```bash
docker compose up -d --build
```

O primeiro build leva de 3 a 10 minutos e faz o seguinte:

1. **backend:** o Maven compila o código com bytecode Java 7 (`-source/-target 1.7`), roda os testes JUnit, gera o `agenda-backend.war` e o copia para um Tomcat 7 com JRE 7 como `ROOT.war`.
2. **frontend:** baixa o Apache Flex SDK 4.16.1 e o `playerglobal.swc`, compila `Agenda.mxml` com o `mxmlc` para gerar o `Agenda.swf` e publica esse arquivo no nginx.
3. **db:** sobe o MySQL 5.7 e executa `db/init.sql`, que cria as tabelas e insere 3 contatos de exemplo.

### 4. Acompanhar a inicialização

```bash
docker compose ps                 # "agenda-db" deve ficar (healthy)
docker compose logs -f backend    # espere por "Server startup in ... ms"
```

O backend só inicia depois que o MySQL passa no healthcheck.

### 5. Verificar o backend

Abra no navegador ou use o curl:

```bash
curl http://localhost:8081/api/health
# {"java":"1.7.0_...","servidor":"Apache Tomcat/7.0.x","banco":"MySQL 5.7.x","status":"UP"}

curl http://localhost:8081/api/contatos
```

O campo `"java":"1.7.0_..."` confirma que o backend está rodando em Java 7.

Para testar o CRUD completo pela linha de comando:

```bash
chmod +x testar-api.sh
./testar-api.sh
```

### 6. Abrir a aplicação Flex

Acesse **http://localhost:8080**.

Os navegadores atuais não têm mais o plugin Flash. Por isso, o `index.html` carrega o **[Ruffle](https://ruffle.rs)**, um emulador de Flash Player em WebAssembly, que executa o `Agenda.swf` direto na página.

Na tela:

1. A grade à esquerda lista os contatos. Clique em um deles para carregá-lo no formulário.
2. **Novo contato** limpa o formulário. Preencha o nome e use o botão **+** para adicionar cada telefone e cada e-mail (ou tecle Enter).
3. **Salvar** cria o contato (POST) ou atualiza o que está aberto (PUT).
4. **Excluir** pede confirmação e remove o contato (DELETE).
5. **Buscar** filtra por nome, e-mail ou telefone.

**Alternativa com Flash Player de verdade:** baixe o *Flash Player Projector (content debugger)* na página de downloads de debug da Adobe, abra o projector e use *File → Open* com `http://localhost:8080/Agenda.swf`. Como a URL da API é relativa (`api`), ela aponta para `http://localhost:8080/api`.

### 7. Acessar o banco (opcional)

```bash
docker compose exec db mysql -uagenda -pagenda agenda \
  -e "SELECT c.id, c.nome, t.numero FROM contato c LEFT JOIN contato_telefone t ON t.contato_id = c.id;"
```

Você também pode usar um cliente gráfico (DBeaver, MySQL Workbench) em `localhost:3307`, com usuário `agenda` e senha `agenda`.

### 8. Parar, reiniciar e limpar

```bash
docker compose stop                 # para os containers (os dados ficam)
docker compose start                # sobe de novo
docker compose down                 # remove os containers (os dados ficam no volume)
docker compose down -v              # remove também o volume do MySQL (o init.sql roda de novo)
docker compose up -d --build frontend   # recompila só o frontend depois de editar o MXML
docker compose up -d --build backend    # recompila só o backend depois de editar o Java
```

---

## Migração para HTML5 (Apache Royale + agentes Claude)

A pasta `migracao/` tem um pipeline que migra esta tela Flex para HTML5/CSS/JS. Ele usa dois agentes
da Claude Platform e o compilador Apache Royale, que roda dentro do container do Flex (estágio
`migrador` do `frontend/Dockerfile`). O resultado é o projeto `../agenda-contatos-html5`, que usa
a mesma API Java 7.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose --profile migracao run --rm migrador
cd ../agenda-contatos-html5 && docker compose up -d --build   # http://localhost:8082
```

O passo a passo, as etapas, as validações e os logs estão em [migracao/README.md](migracao/README.md).

---

## API REST

Endereço base: `http://localhost:8081/api` (direto no Tomcat) ou `http://localhost:8080/api` (pelo nginx).

| Método | URL | Descrição | Sucesso |
|---|---|---|---|
| GET | `/contatos?q=texto` | Lista os contatos; `q` filtra por nome, e-mail ou telefone | 200 |
| GET | `/contatos/{id}` | Busca um contato | 200 / 404 |
| POST | `/contatos` | Cria um contato | 201 |
| PUT | `/contatos/{id}` | Atualiza um contato (as listas são substituídas) | 200 / 404 |
| DELETE | `/contatos/{id}` | Exclui um contato | 200 / 404 |
| GET | `/health` | Mostra a versão do Java, do Tomcat e do banco | 200 / 503 |

Exemplo de corpo JSON:

```json
{
  "nome": "Ana Beatriz Sousa",
  "telefones": ["(86) 3215-5500", "(86) 99999-1234"],
  "emails": ["ana@ufpi.edu.br"],
  "endereco": { "rua": "Av. Universitária, 1310", "cep": "64049-550",
                "cidade": "Teresina", "estado": "PI", "pais": "Brasil" }
}
```

Os erros voltam como `{"erro": "...", "status": 400, "detalhes": [...]}`.

### Adaptações para o Flash Player

O Flash Player tem limitações de rede que o backend contorna. Todas estão implementadas em `ApiServlet.java` e `ApiClient.as`:

| Limitação do Flash | Solução |
|---|---|
| Só envia GET e POST | O cliente manda `POST ...?_method=PUT` (ou `DELETE`), e o servlet redireciona internamente para `doPut`/`doDelete`. O header `X-HTTP-Method-Override` também é aceito. |
| Não entrega o corpo de respostas 4xx/5xx ao ActionScript | Com `?suppress_response_codes=true`, o servidor responde sempre 200 e coloca o erro no JSON. |
| Um POST sem corpo vira GET | O DELETE envia `{}` como corpo. |
| O navegador guarda GETs em cache | O cliente acrescenta `_ts=<timestamp>`, e o servidor envia `Cache-Control: no-cache`. |
| Política de acesso entre domínios | O SWF e a API ficam na mesma origem por meio do nginx. Mesmo assim, o Tomcat publica um `crossdomain.xml` para acesso direto na porta 8081. |

---

## Estrutura do projeto

```
agenda-contatos/
├── docker-compose.yml
├── testar-api.sh                     # teste do CRUD com curl
├── db/                              # Dockerfile (mysql:5.7) + init.sql (esquema e dados de exemplo)
├── backend/                          # Java 7 + Tomcat 7
│   ├── Dockerfile                    # Maven (build) → tomcat:7-jre7 (runtime)
│   ├── pom.xml                       # source/target 1.7, mysql-connector 5.1.49, gson 2.8.9
│   └── src/main/java/br/ufpi/agenda/
│       ├── model/    Contato, Endereco
│       ├── dao/      ConnectionFactory, ContatoDao (JDBC, transações, try-with-resources)
│       ├── service/  ContatoService, ContatoValidator, ValidacaoException
│       └── web/      ApiServlet (base REST + adaptações para o Flash), ContatoServlet, HealthServlet
└── frontend/                         # Adobe Flex
    ├── Dockerfile                    # Apache Flex SDK + mxmlc → nginx
    ├── nginx.conf                    # arquivos estáticos + proxy /api → backend
    ├── html/index.html               # página que carrega o SWF via Ruffle
    ├── lib/                          # (opcional) playerglobal.swc local
    └── src/
        ├── Agenda.mxml               # tela: grade + formulário
        └── br/ufpi/agenda/ApiClient.as   # cliente REST (HTTPService + JSON)
```

Recursos do Java 7 usados no backend: operador diamond (`new ArrayList<>()`), try-with-resources, multi-catch (`SQLException | RuntimeException`) e `switch` com `String`. O código evita APIs do Java 8, como `String.join`, streams e `java.time`, porque roda em uma JRE 7 real.

---

## Solução de problemas

| Sintoma | Causa provável e solução |
|---|---|
| `no matching manifest for linux/arm64` | Você está em Apple Silicon sem emulação. Ative o Rosetta no Docker Desktop (veja o passo 1). |
| O build do frontend falha ao baixar o SDK (`archive.apache.org`) | Pode ser rede ou proxy corporativo. Tente de novo ou use um espelho: `docker compose build --build-arg FLEX_SDK_URL=<url> frontend`. |
| O build do frontend falha ao baixar o `playerglobal.swc` | Copie um `playerglobal.swc` (versão 11.1 ou superior) para `frontend/lib/` e rode `docker compose build frontend` de novo. |
| `mxmlc` reclama de `flex-config.xml` ou de `playerglobal` | Confira se o arquivo ficou em `/opt/flex/frameworks/libs/player/11.1/playerglobal.swc`: `docker build --target build -t flex-debug frontend && docker run --rm -it flex-debug bash`. |
| A página abre, mas o SWF não aparece | O navegador pode estar bloqueando o `unpkg.com`, de onde o Ruffle é carregado. Libere o domínio ou baixe o Ruffle *self-hosted* e troque o `<script src>` no `index.html`. Outra opção é usar o Flash Player Projector (passo 6). |
| A tela diz "Falha de comunicação" | O backend ainda está subindo. Veja `docker compose logs backend` e `curl localhost:8081/api/health`. |
| `/api/health` retorna `"status":"DOWN"` | O MySQL não está pronto ou houve erro de credenciais. Veja `docker compose logs db`. |
| `Communications link failure` logo após o `up` | O MySQL emulado em amd64 pode demorar a iniciar. O backend depende do healthcheck do banco; aguarde e recarregue a página. |
| Mudei o `init.sql` e nada aconteceu | O script só roda com o volume vazio. Use `docker compose down -v` e depois `up -d`. |
| Porta ocupada | Troque o lado esquerdo do mapeamento no `docker-compose.yml`, por exemplo `"9090:80"`. |
