# Aplicação HTML5 gerada pelo pipeline de migração Flex -> Apache Royale.
# Não há etapa de build aqui: o pipeline já compilou o código Royale para www/ (HTML5 + CSS + JS).
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY www/ /usr/share/nginx/html/
RUN chmod 644 /etc/nginx/conf.d/default.conf && chmod -R a+rX /usr/share/nginx/html
EXPOSE 80
