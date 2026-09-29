# MySQL 5.7 com o script de inicialização embutido na imagem
# (evita problemas de permissão de bind mount no Docker Desktop)
FROM mysql:5.7
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
RUN chmod 644 /docker-entrypoint-initdb.d/01-init.sql
