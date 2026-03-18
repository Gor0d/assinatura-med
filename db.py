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
except oracledb.ProgrammingError:
    pass  # já inicializado anteriormente — seguro ignorar
except Exception as e:
    raise RuntimeError(f"Falha ao inicializar Oracle Client em '{_instant_client}': {e}") from e

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

def listar_assinaturas(filtro: str = "") -> list[dict]:
    """Retorna todos os prestadores com assinatura cadastrada."""
    sql = """
        SELECT pa.CD_PRESTADOR,
               p.NM_PRESTADOR,
               p.DS_CODIGO_CONSELHO
        FROM PRESTADOR_ASSINATURA pa
        JOIN PRESTADOR p ON p.CD_PRESTADOR = pa.CD_PRESTADOR
        WHERE pa.ASSINATURA_TISS IS NOT NULL
    """
    params = {}
    if filtro:
        sql += " AND (UPPER(p.NM_PRESTADOR) LIKE :f OR CAST(pa.CD_PRESTADOR AS VARCHAR2(20)) LIKE :f)"
        params["f"] = f"%{filtro.upper()}%"
    sql += " ORDER BY p.NM_PRESTADOR"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, **params)
            rows = cur.fetchall()

    return [
        {"cd_prestador": r[0], "nm_prestador": r[1], "crm": r[2]}
        for r in rows
    ]


def excluir_assinatura(cd_prestador: int) -> None:
    """Remove o registro de assinatura do prestador."""
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM PRESTADOR_ASSINATURA WHERE CD_PRESTADOR = :cd",
                cd=cd_prestador,
            )
        conn.commit()


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


def buscar_assinatura_atual(cd_prestador: int) -> dict:
    """
    Verifica se existe assinatura e tenta retornar os bytes para exibição.
    Retorna dict com:
      - existe (bool)
      - imagem (bytes | None) — None se existir mas não conseguir exibir
    """
    from PIL import Image
    import io as _io

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
                return {"existe": False, "imagem": None}

            # LOB deve ser lido DENTRO do bloco com conexão ativa
            valor = row[0]
            if hasattr(valor, "read"):
                valor = valor.read()

    # Tenta decodificar base64 primeiro, depois usa raw
    for candidato in [_tentar_base64(valor), bytes(valor)]:
        try:
            Image.open(_io.BytesIO(candidato)).verify()
            return {"existe": True, "imagem": candidato}
        except Exception:
            continue

    # Tem registro mas não consegue exibir (formato proprietário do MV)
    return {"existe": True, "imagem": None}


def _tentar_base64(dados: bytes) -> bytes:
    return base64.b64decode(dados)


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
