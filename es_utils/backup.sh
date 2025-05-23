#!/bin/bash

# ✅ Permite passar como variável de ambiente ou como argumento
# Ordem de prioridade: argumentos > variáveis de ambiente > erro

# → Pega ES_URL
ES_URL="${1:-$ES_URL}"
# → Pega AUTH
AUTH="${2:-$AUTH}"

# 🚫 Verifica se os parâmetros estão presentes
if [[ -z "$ES_URL" || -z "$AUTH" ]]; then
  echo "❌ Uso incorreto."
  echo "Uso correto:"
  echo "  ./backup.sh <ES_URL> <AUTH>"
  echo ""
  echo "Ou defina como variáveis de ambiente:"
  echo "  ES_URL=... AUTH=... ./backup.sh"
  exit 1
fi

echo "🔗 ES_URL: $ES_URL"
echo "🔐 AUTH: $AUTH"

# 🔧 Criação do repositório de snapshot (idempotente)
curl -u "$AUTH" -X PUT "$ES_URL/_snapshot/opoca_backup" -H 'Content-Type: application/json' -k -d '
{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/backup",
    "compress": true
  }
}'

# 📦 Criar snapshot com timestamp
SNAPSHOT_NAME="snapshot_$(date +%Y%m%d_%H%M%S)"

curl -u "$AUTH" -X PUT "$ES_URL/_snapshot/opoca_backup/$SNAPSHOT_NAME" \
  -H 'Content-Type: application/json' -k -d '
{
  "indices": "opoca",
  "ignore_unavailable": true,
  "include_global_state": false
}'

echo "✅ Backup criado com nome: $SNAPSHOT_NAME"
