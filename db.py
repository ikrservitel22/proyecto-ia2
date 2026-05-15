import sqlite3

def init_db():
    conn = sqlite3.connect("errors.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS errores (
        id INTEGER PRIMARY KEY,
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

    c.execute("""
        SELECT codigo, sistema, causa, solucion
        FROM errores
        WHERE codigo LIKE ? OR sistema LIKE ? OR causa LIKE ?
    """, (f"%{texto}%", f"%{texto}%", f"%{texto}%"))

    return c.fetchall()