
# 📄 Documentação de Processamento dos Dados do OpenAlex no Projeto OCABr

## Visão Geral

Para incluir os dados do OpenAlex no projeto OCABr, é necessário executar uma sequência de comandos de linha de comando.

A ordem é **fundamental**, pois existem dependências entre os dados e os índices auxiliares do Elasticsearch.

---

## 1. Criação dos Índices Auxiliares

Execute o script para criar os índices auxiliares no Elasticsearch:

```bash
python manage.py runscript create_auxiliary_indexes
```

### Esse script irá criar os seguintes índices:

- `regionsbra` → Dados de cidades, estados e regiões do Brasil
- `regionscon` → Dados das regiões continentais (América do Sul, Europa, etc.)
- `thematicareas` → Dados das áreas temáticas associadas aos conceitos

---

## 2. Processamento dos Registros OpenAlex

Execute o seguinte script para processar os arquivos `.jsonl` do OpenAlex, enriquecendo e indexando no Elasticsearch.

### Com multiprocessing ativado:

```bash
python manage.py runscript process_works --script-args /caminho/dos/arquivos 1 4 INFO False
```

- `/caminho/dos/arquivos` → Diretório onde estão os arquivos `.jsonl` ou `.jsonl.gz`
- `1` → Limita a quantidade de arquivos (opcional)
- `4` → Número de processos paralelos (opcional)
- `INFO` → Nível de log (`DEBUG`, `INFO`, `WARN`, `ERROR`)
- `False` → Desabilita multiprocessing (`False` para usar multiprocessing)

### Sem multiprocessing:

```bash
python manage.py runscript process_works --script-args /caminho/dos/arquivos 10 2 DEBUG True
```

- Último parâmetro `True` significa **desabilitar multiprocessing**, processando em modo sequencial.

### Execução mínima (obrigatório apenas o diretório):

```bash
python manage.py runscript process_works --script-args /caminho/dos/arquivos
```

---

## 3. Download dos Dados do OpenAlex

Para baixar a base de dados completa (snapshot) do OpenAlex:

```bash
aws s3 sync "s3://openalex/data/works" "openalex-snapshot" --no-sign-request
```

- Isso fará o download de todos os arquivos de **trabalhos acadêmicos (works)** para o diretório `openalex-snapshot`.

---

## 4. Organização dos Arquivos por Ano

Agrupar os arquivos JSONL em pastas separadas por ano para facilitar o processamento.

### Uso:

```bash
python manage.py runscript group_by_year --script-args <data_dir> <out_dir> <start_year> <end_year> <processes> <log_level>
```

### Exemplo de execução:

```bash
python manage.py runscript group_files_works_by_year --script-args /caminho/openalex/snapshot /caminho/output 2020 2024 1 DEBUG
```

- `/caminho/openalex/snapshot` → Diretório de origem dos arquivos `.jsonl.gz` do OpenAlex
- `/caminho/output` → Diretório de destino para os arquivos organizados por ano
- `2020` → Ano inicial
- `2024` → Ano final
- `1` → Número de processos
- `DEBUG` → Nível de log

---

## Resumo da Sequência Recomendada

**Criar os índices auxiliares:**

```bash
python manage.py runscript create_auxiliary_indexes
```

**Organizar os dados do OpenAlex por ano:**

```bash
python manage.py runscript group_files_works_by_year --script-args /snapshot /output 2020 2024 2 INFO
```

**Processar os registros do OpenAlex e enviar ao Elasticsearch:**

```bash
python manage.py runscript process_works --script-args /output
```


## Observação Importante

- A sequência de execução é **obrigatória**.
- A criação dos índices auxiliares deve ocorrer **antes** de processar os dados do OpenAlex.
- Os scripts fazem enriquecimento geográfico e temático, baseando-se nos índices auxiliares (`regionsbra`, `regionscon`, `thematicareas`).

