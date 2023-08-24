from flask import Flask, send_from_directory, Response
from flask_cors import CORS
import os
import sqlite3

app = Flask(__name__, static_folder='gw-client/dist')
CORS(app)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        if path.endswith('.js'):
            with open(os.path.join(app.static_folder, path), 'r') as f:
                response = Response(f.read(), mimetype='application/javascript')
                return response
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/scrapes')
def get_scrapes():
    conn = get_conn()

    # Get all scrapes
    c = conn.cursor()
    c.execute('SELECT * FROM Scrape')
    scrapes = c.fetchall()

    # Return as json
    return {'scrapes': scrapes}

@app.route('/api/scrapes/<int:scrape_id>')
def get_scrape(scrape_id):
    conn = get_conn()

    # Get scrape
    c = conn.cursor()
    c.execute('SELECT * FROM Scrape WHERE id = ?', (scrape_id,))
    scrape = c.fetchone()

    # Get destinations
    c.execute('SELECT * FROM Destination WHERE scrape_id = ?', (scrape_id,))
    scrape['destinations'] = c.fetchall()

    # Get flights
    for destination in scrape['destinations']:
        c.execute('SELECT * FROM Flight WHERE dest_id = ?', (destination['id'],))
        destination['flights'] = c.fetchall()

    # Return as json
    return {'scrape': scrape}

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_conn():
    # Check file exists
    if not os.path.isfile('gowild.db'):
        raise Exception('gowild.db not found')

    # Get connection to sqlite database
    conn = sqlite3.connect('gowild.db')
    conn.row_factory = dict_factory
    return conn


if __name__ == '__main__':
    app.run(port=5555)
