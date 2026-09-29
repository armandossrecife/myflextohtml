# ---------- Etapa 1: build com Maven (bytecode Java 7) ----------
# A etapa de build roda na arquitetura nativa da máquina ($BUILDPLATFORM),
# o que deixa o Maven rápido mesmo em Macs Apple Silicon.
FROM --platform=$BUILDPLATFORM maven:3.8.8-eclipse-temurin-8 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B package

# ---------- Etapa 2: runtime Tomcat 7 + JRE 7 ----------
FROM tomcat:7-jre7
ENV TZ=America/Fortaleza
RUN rm -rf /usr/local/tomcat/webapps/*
COPY --from=build /app/target/agenda-backend.war /usr/local/tomcat/webapps/ROOT.war
EXPOSE 8080
CMD ["catalina.sh", "run"]
