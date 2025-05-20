import datetime
import gzip
import logging
import multiprocessing
import os
import time
from pathlib import Path

import orjson
from tqdm import tqdm


def configure_logger(level: str = "INFO"):
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("group_by_year")
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def process_file_by_years(args):
    file_path, start_year, end_year, output_dir = args
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with gzip.open(file_path, "rt") as infile:
            for line in infile:
                try:
                    record = orjson.loads(line)
                    year = record.get("publication_year")
                    if year and start_year <= year <= end_year:
                        jsonl_path = output_dir / f"works-{year}.jsonl"
                        with open(jsonl_path, "ab") as outfile:
                            outfile.write(orjson.dumps(record) + b"\n")
                except orjson.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️ Erro ao processar linha em {file_path}: {e}")
        for year in range(start_year, end_year + 1):
            jsonl_path = output_dir / f"works-{year}.jsonl"
            gz_path = output_dir / f"works-{year}.jsonl.gz"
            if jsonl_path.exists():
                with open(jsonl_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
                    f_out.writelines(f_in)
                os.remove(jsonl_path)
    except Exception as e:
        print(f"❌ Erro ao abrir o arquivo {file_path}: {e}")


def run(*args):
    """
    Uso:
        python manage.py runscript group_by_year --script-args <data_dir> <out_dir> <start_year> <end_year> <processes> <log_level>

    Exemplo:
        python manage.py runscript  group_files_works_by_year --script-args /Volumes/Data/openalex-slim fixtures 2015 2022 1 DEBUG
    """
    if len(args) < 2:
        print("❌ ERRO: É necessário pelo menos <data_dir> e <out_dir>.")
        return

    data_dir = Path(args[0])
    out_dir = Path(args[1])
    start_year = int(args[2]) if len(args) > 2 else 2014
    end_year = int(args[3]) if len(args) > 3 else 2025
    processes = int(args[4]) if len(args) > 4 else os.cpu_count()
    log_level = args[5] if len(args) > 5 else "INFO"

    logger = configure_logger(log_level)
    logger.info("Iniciando agrupamento de registros por ano com multiprocessamento...")

    arquivos = list(data_dir.glob("**/*.gz"))
    pool_args = [(arquivo, start_year, end_year, out_dir) for arquivo in arquivos]

    start_time = time.time()

    with multiprocessing.Pool(processes=processes) as pool:
        list(
            tqdm(
                pool.imap_unordered(process_file_by_years, pool_args),
                total=len(pool_args),
            )
        )

    elapsed = time.time() - start_time
    formatted = str(datetime.timedelta(seconds=int(elapsed)))
    logger.info(f"Tempo total de execução: {formatted}")
