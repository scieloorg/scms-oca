Para realizar backup do índice do Elasticsearch: 

```
./backup.sh https://node01-elk.scielo.org:9200 elastic:senha
```

Para realizar restore do índice do Elasticsearch: 

```
./restore.sh https://node01-elk.scielo.org:9200 elastic:senha snapshot_20240523_101512