import chess
import chess.engine
import sqlite3
import requests
import json
import time

MIN_GAMES = 100000
SPEEDS = ['blitz']
RATINGS = ['1400', '1600', '1800'] # Covers openings between roughly 40th and 90th percentiles
# TODO: Add starting opening option

DB_FILE = 'positions.db'
ENGINE_PATH = '/opt/homebrew/Cellar/stockfish/17.1/bin/stockfish'
ENGINE_DEPTH = 20

def get_position_moves(fen, token):
    params = {
        'variant': 'standard',
        'fen': fen,
        'speeds': ','.join(SPEEDS),
        'ratings': ','.join(RATINGS),
        'moves': 20, # Chosen because there are 20 possibilities for white's first move
        'topGames': 0,
        'recentGames': 0
    }
    headers = { 'Authorization': 'Bearer ' + token }

    try:
        resp = requests.get("https://explorer.lichess.ovh/lichess", params=params, headers=headers)
        if resp.status_code == 429:
            print("Made too many requests. Trying again in 60 seconds.")
            time.sleep(60)
            return get_position_moves(fen, token)
        return json.loads(resp.text)
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e :
        print("Request failed. Trying again in 60 seconds.")
        time.sleep(60)
        return get_position_moves(fen, token)

def get_cloud_analysis(fen, token):
    params = {
        'fen': fen,
        'variant': 'standard'
    }
    headers = { 'Authorization': 'Bearer ' + token }

    try:
        resp = requests.get("https://lichess.org/api/cloud-eval", params=params, headers=headers)
        if resp.status_code == 404: # Position not in cloud database
            return None
        elif resp.status_code == 429:
            print("Made too many requests. Trying again in 60 seconds.")
            time.sleep(60)
            return get_cloud_analysis(fen, token)
        analysis = json.loads(resp.text)
        depth = analysis['depth']
        eval = analysis['pvs'][0]['cp']
        return {
            'eval': eval,
            'depth': depth
        }
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e :
        print("Request failed. Trying again in 60 seconds.")
        time.sleep(60)
        return get_cloud_analysis(fen, token)

# Returns board's FEN but without the half-move clock or the turn count
def simple_fen(board):
    fen = board.fen()
    parts = fen.split(' ')[:4]
    return ' '.join(parts)

def add_position(board, token, engine, cursor):
    fen = simple_fen(board)
    plays = get_position_moves(fen, token)

    # Get position evaluation from Lichess cloud or local engine
    analysis = get_cloud_analysis(fen, token)
    if analysis is None:
        analysis = engine.analyse(board, chess.engine.Limit(depth=ENGINE_DEPTH))
        eval = analysis['score'].white().score(mate_score=1000000)
        depth = ENGINE_DEPTH
    else:
        eval = analysis['eval']
        depth = analysis['depth']

    white = plays['white']
    draw = plays['draws']
    black = plays['black']

    cursor.execute("""
        INSERT INTO position (position_fen, eval, depth, white, draw, black)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [fen, eval, depth, white, draw, black])

    for move in plays['moves']:
        uci = move['uci']
        san = move['san']
        new_board = chess.Board(fen)
        new_board.push(chess.Move.from_uci(uci))

        white = move['white']
        draw = move['draws']
        black = move['black']

        cursor.execute("""
            INSERT INTO move (position_fen, move_san, move_uci, result_fen, white, draw, black)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [fen, uci, san, simple_fen(new_board), white, draw, black])

def main():
    with open('token.txt', 'r') as f:
        token = f.read().strip()

    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if there are any positions in database
    cursor.execute("""
        SELECT COUNT(1) FROM position
    """)
    result = cursor.fetchall()
    row_count = result[0][0]
    if row_count == 0:
        board = chess.Board()
        add_position(board, token, engine, cursor)
        conn.commit()

    while True:
        # Start from the most played move that hasn't been evaluated yet
        cursor.execute("""
            SELECT result_fen, SUM(white + draw + black) AS total FROM move
            WHERE result_fen NOT IN (
                SELECT position_fen
                FROM position
            )
            GROUP BY result_fen
            HAVING total >=?
            ORDER BY total DESC
            LIMIT 50
        """, [MIN_GAMES])
        results = cursor.fetchall()
        if len(results) == 0:
            print(f'Mapped every move played at least {MIN_GAMES} times')
            break
        for position in results:
            board = chess.Board(position[0])
            print(f'Adding {position[0]} with {position[1]} plays')
            add_position(board, token, engine, cursor)
            conn.commit()

    conn.close()
    engine.quit()

if __name__ == '__main__':
    main()
