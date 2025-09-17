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
            game_count INTEGER -- Number of Lichess games that reached this position
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS move (
            position_fen TEXT,
            move_uci TEXT, -- Move in UCI notation (for engines)
            move_san TEXT, -- Move in Standard Algebraic Notation (for humans)
            made_count INTEGER, -- Number of games that progressed with this move
            result_fen TEXT,
            PRIMARY KEY (position_fen, move_uci),
            FOREIGN KEY (position_fen) REFERENCES position(position_fen)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
