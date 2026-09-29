#!/usr/bin/env bash
# Testa o CRUD da API REST com curl (backend exposto em http://localhost:8081).
# Uso: ./testar-api.sh [URL_BASE]
set -euo pipefail
API="${1:-http://localhost:8081/api}"
JSON='Content-Type: application/json'

passo() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }

passo "Health check"
curl -s "$API/health"; echo

passo "Listar contatos"
curl -s "$API/contatos"; echo

passo "Criar contato (POST)"
CRIADO=$(curl -s -X POST -H "$JSON" "$API/contatos" -d '{
  "nome": "Teste via curl",
  "telefones": ["(86) 3000-0000", "(86) 98888-0000"],
  "emails": ["teste@exemplo.com"],
  "endereco": {"rua": "Rua A, 10", "cep": "64000-000", "cidade": "Teresina", "estado": "PI", "pais": "Brasil"}
}')
echo "$CRIADO"
ID=$(echo "$CRIADO" | sed -E 's/.*"id":([0-9]+).*/\1/')

passo "Buscar contato $ID (GET)"
curl -s "$API/contatos/$ID"; echo

passo "Atualizar contato $ID (PUT)"
curl -s -X PUT -H "$JSON" "$API/contatos/$ID" -d '{
  "nome": "Teste via curl (editado)",
  "telefones": ["(86) 97777-0000"],
  "emails": ["novo@exemplo.com", "outro@exemplo.com"],
  "endereco": {"rua": "Rua B, 20", "cep": "64000-111", "cidade": "Parnaíba", "estado": "PI", "pais": "Brasil"}
}'; echo

passo "Atualizar como o Flash faz (POST + _method=PUT + suppress_response_codes)"
curl -s -X POST -H "$JSON" "$API/contatos/$ID?_method=PUT&suppress_response_codes=true" \
     -d '{"nome": "Teste via Flash", "telefones": [], "emails": [], "endereco": {}}'; echo

passo "Erro de validação (nome vazio) -> HTTP 400"
curl -s -w '  [HTTP %{http_code}]' -X POST -H "$JSON" "$API/contatos" -d '{"nome": " "}'; echo

passo "Excluir contato $ID (DELETE)"
curl -s -X DELETE "$API/contatos/$ID"; echo

passo "Buscar contato excluído -> HTTP 404"
curl -s -w '  [HTTP %{http_code}]' "$API/contatos/$ID"; echo
