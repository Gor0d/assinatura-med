"""
Log de auditoria — registra todas as operações de assinatura.
Salva em /app/logs/auditoria.jsonl (persistido via volume Docker).
"""

import json
import os
from datetime import datetime
from pathlib import Path

LOG_DIR  = Path(os.environ.get("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "auditoria.jsonl"


def _garantir_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def registrar(operador: str, cd_prestador: int, nm_prestador: str,
              operacao: str, obs: str = "") -> None:
    """Grava uma linha de log no arquivo JSONL."""
    _garantir_dir()
    entrada = {
        "dt_operacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operador":    operador,
        "cd_prestador": cd_prestador,
        "nm_prestador": nm_prestador,
        "operacao":    operacao,   # INSERT ou UPDATE
        "obs":         obs,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def carregar_logs() -> list[dict]:
    """Retorna todos os registros de auditoria em ordem decrescente."""
    _garantir_dir()
    if not LOG_FILE.exists():
        return []
    linhas = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    linhas.append(json.loads(linha))
                except json.JSONDecodeError:
                    pass
    return list(reversed(linhas))
