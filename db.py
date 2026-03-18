"""
Operações de banco de dados Oracle para assinaturas médicas.
"""

import base64
import os
import oracledb

# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def conectar() -> oracledb.Connection:
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=oracledb.makedsn(
            os.environ["DB_HOST"],
            int(os.environ.get("DB_PORT", 1521)),
            sid=os.environ["DB_SID"],
        ),
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
    Insere ou atualiza a assinatura nas colunas ASSINATURA (Long Raw)
    e ASSINATURA_TISS (BLOB) em base64.
    Retorna 'INSERT' ou 'UPDATE'.
    """
    b64 = base64.b64encode(img_bytes)  # bytes base64

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(1) FROM PRESTADOR_ASSINATURA WHERE CD_PRESTADOR = :cd",
                cd=cd_prestador,
            )
            existe = cur.fetchone()[0] > 0

            if existe:
                cur.execute(
                    """
                    UPDATE PRESTADOR_ASSINATURA
                    SET ASSINATURA      = :assinatura,
                        ASSINATURA_TISS = :assinatura_tiss
                    WHERE CD_PRESTADOR  = :cd
                    """,
                    assinatura=b64,
                    assinatura_tiss=b64,
                    cd=cd_prestador,
                )
                operacao = "UPDATE"
            else:
                cur.execute(
                    """
                    INSERT INTO PRESTADOR_ASSINATURA
                        (CD_PRESTADOR, ASSINATURA, ASSINATURA_TISS)
                    VALUES
                        (:cd, :assinatura, :assinatura_tiss)
                    """,
                    cd=cd_prestador,
                    assinatura=b64,
                    assinatura_tiss=b64,
                )
                operacao = "INSERT"

        conn.commit()

    return operacao
