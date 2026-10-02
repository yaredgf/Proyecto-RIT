import psycopg
from psycopg.rows import dict_row

from crawler_rit.settings import RIT_POSTGRES


def conectar():
    """Abre una conexión usando la configuración del proyecto."""
    return psycopg.connect(
        **RIT_POSTGRES,
        connect_timeout=10,
        row_factory=dict_row,
    )


def verificar():
    """Comprueba la conexión y la existencia de las seis tablas."""
    tablas_esperadas = {
        "sitios",
        "ciclos",
        "documentos",
        "versiones",
        "identificadores",
        "menciones",
    }

    with conectar() as conexion:
        base = conexion.execute(
            "SELECT current_database() AS nombre"
        ).fetchone()

        filas = conexion.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        ).fetchall()

    tablas_existentes = {fila["table_name"] for fila in filas}
    faltantes = tablas_esperadas - tablas_existentes

    if faltantes:
        raise RuntimeError(
            "Faltan tablas: " + ", ".join(sorted(faltantes))
        )

    print(f"Conexión correcta: {base['nombre']}")
    print("Las seis tablas requeridas existen.")


if __name__ == "__main__":
    verificar()