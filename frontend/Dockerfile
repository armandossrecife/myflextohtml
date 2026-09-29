# ---------- Etapa 1: compilar o SWF com o Apache Flex SDK ----------
FROM eclipse-temurin:8-jdk AS build

ARG FLEX_VERSION=4.16.1
ARG FLEX_SDK_URL=https://archive.apache.org/dist/flex/${FLEX_VERSION}/binaries/apache-flex-sdk-${FLEX_VERSION}-bin.tar.gz
# O playerglobal.swc (API do Flash Player) é da Adobe e não vem no SDK da Apache.
# O site original da Adobe saiu do ar; usamos um espelho público. Pode ser trocado via --build-arg
# ou colocando o arquivo em frontend/lib/playerglobal.swc.
ARG PLAYERGLOBAL_URL=https://raw.githubusercontent.com/nexussays/playerglobal/master/11.1/playerglobal.swc

ENV FLEX_HOME=/opt/flex
ENV PLAYERGLOBAL_HOME=/opt/flex/frameworks/libs/player

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Apache Flex SDK
RUN mkdir -p "$FLEX_HOME" \
 && curl -fSL --retry 3 "$FLEX_SDK_URL" -o /tmp/flex.tar.gz \
 && tar -xzf /tmp/flex.tar.gz -C "$FLEX_HOME" --strip-components=1 \
 && rm /tmp/flex.tar.gz \
 && if [ ! -f "$FLEX_HOME/frameworks/flex-config.xml" ] && [ -f "$FLEX_HOME/frameworks/flex-config-template.xml" ]; then \
      sed -e 's/@playerversion@/11.1/g' -e 's/@swfversion@/14/g' \
          "$FLEX_HOME/frameworks/flex-config-template.xml" > "$FLEX_HOME/frameworks/flex-config.xml"; \
    fi

# playerglobal.swc (arquivo local tem prioridade sobre o download)
COPY lib/ /tmp/lib/
RUN mkdir -p "$PLAYERGLOBAL_HOME/11.1" \
 && if [ -f /tmp/lib/playerglobal.swc ]; then \
      cp /tmp/lib/playerglobal.swc "$PLAYERGLOBAL_HOME/11.1/playerglobal.swc"; \
    else \
      curl -fSL --retry 3 "$PLAYERGLOBAL_URL" -o "$PLAYERGLOBAL_HOME/11.1/playerglobal.swc"; \
    fi

WORKDIR /app
COPY src ./src

# -theme Halo ............................. componentes MX com o visual clássico do Flex 3
# -static-link-runtime-shared-libraries ... embute o framework no SWF (sem RSLs externos)
# -target-player 11.1 / -swf-version 14 ... API JSON nativa (Flash Player 11+)
RUN mkdir -p /out \
 && java -Xmx1024m -Djava.awt.headless=true -Dsun.io.useCanonCaches=false \
      -jar "$FLEX_HOME/lib/mxmlc.jar" +flexlib="$FLEX_HOME/frameworks" \
      -source-path=src \
      -theme="$FLEX_HOME/frameworks/themes/Halo/halo.swc" \
      -target-player=11.1 -swf-version=14 \
      -static-link-runtime-shared-libraries=true \
      -debug=false \
      -output=/out/Agenda.swf \
      src/Agenda.mxml \
 && ls -l /out

# ---------- Etapa opcional "migrador": Flex SDK + Apache Royale + agentes Claude ----------
# Estende o container da aplicação Flex (Flex SDK, JDK 8 e código-fonte) com o Apache Royale,
# para que a tradução MXML/AS3 -> HTML5/CSS/JS rode localmente, no mesmo container do Flex.
# Só é construída quando pedida: docker compose --profile migracao build migrador
FROM build AS migrador

ARG ROYALE_VERSION=0.9.12
ARG ANTHROPIC_SDK_VERSION=1.9.0

# O compilador do Royale exige Java 11+; o Flex SDK continua usando o JDK 8 da imagem base.
COPY --from=eclipse-temurin:17-jdk /opt/java/openjdk /opt/jdk17

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*

# Apache Royale (distribuição JS) via npm
RUN npm install --prefix /opt/royale --no-audit --no-fund "@apache-royale/royale-js@${ROYALE_VERSION}" \
 && chmod +x /opt/royale/node_modules/@apache-royale/royale-js/royale-asjs/js/bin/*

# SDK da Claude Platform (Python) num ambiente virtual
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir "anthropic==${ANTHROPIC_SDK_VERSION}"

ENV ROYALE_HOME=/opt/royale/node_modules/@apache-royale/royale-js/royale-asjs \
    ROYALE_JAVA_HOME=/opt/jdk17 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/agenda-contatos/migracao
CMD ["python", "migrar.py", "--help"]

# ---------- Etapa 2: servir o SWF com nginx (e fazer proxy da API) ----------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/
COPY --from=build /out/Agenda.swf /usr/share/nginx/html/Agenda.swf
RUN chmod 644 /etc/nginx/conf.d/default.conf && chmod -R a+rX /usr/share/nginx/html
EXPOSE 80
