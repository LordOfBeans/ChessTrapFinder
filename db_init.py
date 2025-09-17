import sqlite3


DB_FILE = 'positions.db'

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('PRAGMA foreign_keys = 1')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS position (
            position_fen TEXT PRIMARY KEY,
            eval INTEGER,
            depth INTEGER,
            white INTEGER,
            draw INTEGER,
            black INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS move (
            position_fen TEXT,
            move_uci TEXT, -- Move in UCI notation (for engines)
            move_san TEXT, -- Move in Standard Algebraic Notation (for humans)
            result_fen TEXT,
            white INTEGER,
            draw INTEGER,
            black INTEGER,
            PRIMARY KEY (position_fen, move_uci),
            FOREIGN KEY (position_fen) REFERENCES position(position_fen)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
