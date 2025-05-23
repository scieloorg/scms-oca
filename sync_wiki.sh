#!/bin/bash

REPO_WIKI_URL="git@github.com:scieloorg/scms-oca.wiki.git"
WIKI_DIR="scms-oca.wiki"

echo "🧠 Clonando o Wiki..."
rm -rf $WIKI_DIR
git clone $REPO_WIKI_URL $WIKI_DIR

echo "📄 Copiando arquivos da pasta docs para o Wiki..."
cp -r docs/*.md $WIKI_DIR/

cd $WIKI_DIR

echo "🚀 Commitando alterações..."
git add .
git commit -m "Sync Wiki with docs folder from main repo" || echo "⚠️ Nada para commit"
git push

cd ..
rm -rf $WIKI_DIR

echo "✅ Wiki sincronizada com sucesso!"

