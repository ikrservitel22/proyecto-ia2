import sqlite3


def init_db():

    conn = sqlite3.connect("errors.db")

    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS errores (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        codigo TEXT,
        sistema TEXT,
        causa TEXT,
        solucion TEXT
    )
    """)

    conn.commit()
    conn.close()


def buscar_error(texto):

    conn = sqlite3.connect("errors.db")

    c = conn.cursor()

    query = f"%{texto.lower()}%"

    c.execute("""
        SELECT
            codigo,
            sistema,
            causa,
            solucion
        FROM errores
        WHERE
            LOWER(codigo) LIKE ?
            OR LOWER(sistema) LIKE ?
            OR LOWER(causa) LIKE ?
    """, (query, query, query))

    resultados = c.fetchall()

    conn.close()

    return resultados