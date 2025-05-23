#!/bin/bash

# ✅ Permite passar como variável de ambiente ou como argumento
# Ordem de prioridade: argumentos > variáveis de ambiente > erro

# → Pega ES_URL
ES_URL="${1:-$ES_URL}"
# → Pega AUTH
AUTH="${2:-$AUTH}"
# → Nome do snapshot
SNAPSHOT_NAME="${3:-$SNAPSHOT_NAME}"

# 🚫 Verifica se os parâmetros estão presentes
if [[ -z "$ES_URL" || -z "$AUTH" || -z "$SNAPSHOT_NAME" ]]; then
  echo "❌ Uso incorreto."
  echo "Uso correto:"
  echo "  ./restore.sh <ES_URL> <AUTH> <SNAPSHOT_NAME>"
  echo ""
  echo "Ou defina como variáveis de ambiente:"
  echo "  ES_URL=... AUTH=... SNAPSHOT_NAME=... ./restore.sh"
  exit 1
fi

echo "🔗 ES_URL: $ES_URL"
echo "🔐 AUTH: $AUTH"
echo "📦 Snapshot: $SNAPSHOT_NAME"

# 🚀 Executa o restore
curl -u "$AUTH" -X POST "$ES_URL/_snapshot/opoca_backup/$SNAPSHOT_NAME/_restore" \
  -H 'Content-Type: application/json' -k -d '
{
  "indices": "opoca",
  "ignore_unavailable": true,
  "include_global_state": false,
  "rename_pattern": "opoca",
  "rename_replacement": "opoca_restored"
}'

echo "✅ Restauração solicitada para snapshot: $SNAPSHOT_NAME"
