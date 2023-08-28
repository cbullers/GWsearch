from flask import Flask, send_from_directory, Response
from flask_cors import CORS
import os
import sqlite3
import argparse
import requests
import json
import re
from urllib.parse import urlencode
import datetime
import pytz

all_destinations = []
with open('destinations.json', 'r') as f:
    all_destinations = json.load(f)

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
    
def preprocess_dict(d):
    return {k: str(v).lower() if isinstance(v, bool) else v for k, v in d.items()}
    
def get_closest_30min(dt):
    return dt - datetime.timedelta(minutes=dt.minute % 30,
                                   seconds=dt.second,
                                   microseconds=dt.microsecond)
    
@app.route('/api/priceline/<int:depart_flight>/<int:return_flight>/<int:travelers>')
def get_priceline_combo(depart_flight, return_flight, travelers):

    conn = get_conn()
    
    # Get depart flight
    c = conn.cursor()
    c.execute('SELECT * FROM Flight WHERE id = ?', (depart_flight,))
    depart_flight = c.fetchone()
    
    # Get return flight
    c.execute('SELECT * FROM Flight WHERE id = ?', (return_flight,))
    return_flight = c.fetchone()
    
    # Airport code
    iata = depart_flight['dest_iata']
    
    # Get priceline airport entity
    r = requests.session()
    r.headers.update({'User-Agent': 'Mozilla/5.0'})
    res = r.get(f'https://priceline.com/svcs/ac/index/hotels/{iata}')
    items = res.json()['searchItems']
    airport = [item for item in items if item['id'] == iata][0]
    if not airport:
        raise Exception('Airport not found')
        
    # Update to proper fmt
    airport_fmt = {
        'type': 'AIRPORT',
        'name': airport['itemName'],
        'displayName': f"{airport['cityName']}, {airport['stateCode']}",
        'isoCountryCode': airport['country'],
        'id': airport['id'],
        'stateName': airport['provinceName'],
        'countryName': airport['countryName'],
        'latitude': airport['lat'],
        'longitude': airport['lon']
    }
        
    # Build request
    depart_arrival = get_closest_30min(datetime.datetime.strptime(depart_flight['arrival_time'], "%Y-%m-%d %H:%M:%S%z"))
    tz = pytz.timezone(all_destinations[iata]['tz'])
    
    depart_arrival = depart_arrival.astimezone(tz)
    travel_start = depart_arrival.strftime("%m/%d/%Y")
    depart_arrival = depart_arrival.strftime("%Y-%m-%dT%H:%M")
    
    return_departure = get_closest_30min(datetime.datetime.strptime(return_flight['departure_time'], "%Y-%m-%d %H:%M:%S%z"))
    # subtract an hour
    return_departure = return_departure - datetime.timedelta(hours=1)
    return_departure = return_departure.astimezone(tz)
    travel_end = return_departure.strftime("%m/%d/%Y")
    return_departure = return_departure.strftime("%Y-%m-%dT%H:%M")
    
    payload = {
        "components": [
                {
                    "productId": 5,
                    "index": 0,
                    "type": "STAY",
                    "query": {
                        "totalNumRooms": 1
                    }
                },
                {
                    "productId": 8,
                    "type": "DRIVE",
                    "index": 1,
                    "query": {
                        "pickupDateTime": depart_arrival,
                        "returnDateTime": return_departure,
                        "pickupLocation": {
                            "type": "AIRPORT",
                            "id": airport_fmt['id'],
                        },
                        "returnLocation": {
                            "type": "AIRPORT",
                            "id": airport_fmt['id'],
                        },
                        "isIncludeAirportLocations": True
                    }
                }
        ],
        "travelStartDate":travel_start,
        "travelEndDate":travel_end,
        "travelers": {
            "adults": travelers,
            "children": [],
        },
        "origin": airport_fmt,
        "destination": airport_fmt,
        "pivotComponentKey": 0,
        "isRecommendedTrip": False,
        "containsXSell": False,
    }
    
    # Convert to x-www-form-urlencoded
    for key, value in payload.items():
        if isinstance(value, (list, dict)):
            payload[key] = json.dumps(value, separators=(',', ':'))
    
    payload = urlencode(preprocess_dict(payload))
    payload = re.sub(r'%[0-9A-Z]{2}',                             # pattern
                    lambda matchobj: matchobj.group(0).lower(),  # function used to replace matched string
                    payload)                 # input string
    
    # Get priceline combo
    headers = {
        "Host": "www.priceline.com",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": "",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.111 Safari/537.36",
        "Origin": "https://www.priceline.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": "https://www.priceline.com/?tab=vacations",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9"
    }
    res = r.post('https://priceline.com/shop/search', data=payload, headers=headers, allow_redirects=False)
    
    return f"https://priceline.com{res.headers.get('Location')}&sortby=PRICE"
    
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
    parser = argparse.ArgumentParser()
    # arg for port
    parser.add_argument('-p', '--port', type=int, default=42345)
    args = parser.parse_args()

    app.run(port=args.port)
