"""
Operações de banco de dados Oracle para assinaturas médicas.
"""

import base64
import os
import oracledb
from dotenv import load_dotenv

load_dotenv()  # carrega .env se existir (local); em produção usa variáveis do ambiente

# Thick mode — necessário para bancos Oracle com autenticação 10g (DES)
_instant_client = os.environ.get("ORACLE_CLIENT_DIR", r"C:\instantclient_12_2")
try:
    oracledb.init_oracle_client(lib_dir=_instant_client)
except Exception:
    pass  # já inicializado ou caminho não encontrado (thin mode como fallback)

# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def conectar() -> oracledb.Connection:
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT', '1521')}/{os.environ['DB_SERVICE']}",
    )


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def buscar_prestador(cd_prestador: int) -> dict | None:
    """Retorna NM_PRESTADOR e DS_CODIGO_CONSELHO ou None se não encontrado."""
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT NM_PRESTADOR, DS_CODIGO_CONSELHO
                FROM PRESTADOR
                WHERE CD_PRESTADOR = :cd
                """,
                cd=cd_prestador,
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"nm_prestador": row[0], "ds_codigo_conselho": row[1]}


def buscar_assinatura_atual(cd_prestador: int) -> bytes | None:
    """
    Retorna os bytes da assinatura atual (coluna ASSINATURA_TISS / BLOB)
    ou None se não houver registro.
    """
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ASSINATURA_TISS
                FROM PRESTADOR_ASSINATURA
                WHERE CD_PRESTADOR = :cd
                """,
                cd=cd_prestador,
            )
            row = cur.fetchone()
    if row is None or row[0] is None:
        return None

    valor = row[0]
    # BLOB vem como LOB object no oracledb
    if hasattr(valor, "read"):
        valor = valor.read()

    # Se estiver em base64, decodifica para exibir
    try:
        return base64.b64decode(valor)
    except Exception:
        return bytes(valor)


# ---------------------------------------------------------------------------
# INSERT / UPDATE
# ---------------------------------------------------------------------------

def salvar_assinatura(cd_prestador: int, img_bytes: bytes) -> str:
    """
    Insere ou atualiza a assinatura gravando binário diretamente:
      - ASSINATURA      (Long Raw) → bytes via DB_TYPE_LONG_RAW
      - ASSINATURA_TISS (BLOB)     → bytes via DB_TYPE_BLOB
    Retorna 'INSERT' ou 'UPDATE'.
    """
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(1) FROM PRESTADOR_ASSINATURA WHERE CD_PRESTADOR = :cd",
                cd=cd_prestador,
            )
            existe = cur.fetchone()[0] > 0

            if existe:
                cur.setinputsizes(
                    assinatura=oracledb.DB_TYPE_LONG_RAW,
                    assinatura_tiss=oracledb.DB_TYPE_BLOB,
                )
                cur.execute(
                    """
                    UPDATE PRESTADOR_ASSINATURA
                    SET ASSINATURA      = :assinatura,
                        ASSINATURA_TISS = :assinatura_tiss
                    WHERE CD_PRESTADOR  = :cd
                    """,
                    assinatura=img_bytes,
                    assinatura_tiss=img_bytes,
                    cd=cd_prestador,
                )
                operacao = "UPDATE"
            else:
                cur.setinputsizes(
                    assinatura=oracledb.DB_TYPE_LONG_RAW,
                    assinatura_tiss=oracledb.DB_TYPE_BLOB,
                )
                cur.execute(
                    """
                    INSERT INTO PRESTADOR_ASSINATURA
                        (CD_PRESTADOR, ASSINATURA, ASSINATURA_TISS)
                    VALUES
                        (:cd, :assinatura, :assinatura_tiss)
                    """,
                    cd=cd_prestador,
                    assinatura=img_bytes,
                    assinatura_tiss=img_bytes,
                )
                operacao = "INSERT"

        conn.commit()

    return operacao
