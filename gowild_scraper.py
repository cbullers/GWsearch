import random, time, requests, json, html
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import browsercookie
import argparse
import frontier_captcha_solver
import logging
import re
import json
from functools import reduce

'''optional arguments:
  -h, --help            show this help message and exit
  -o ORIGIN, --origin ORIGIN
                        Origin IATA airport code.
  -d DATES, --dates DATES
                        Show flights for: Today: 1 Tommorrow: 2 Both: 3
  -c, --cjs             Use browser cookies.
  --captcha-solver      Use captcha solver (experimental).
  --virtual-display     Use virtual display with the captcha solver (experimental).
  --store-sqlite        Use sqlite3 database to store results.
  -r RESUME, --resume RESUME
                        Index of airport to resume from. Use index 21 to only
                        search for contiguous US destinations.'''
 
# Global Variables
destination_count = 0
destinations_avail = {}
roundtrip_avail = {}

conn = None
scrape_id = None
last_dest_added_id = None

# Load destinations from JSON file
with open("destinations.json", "r") as f:
    all_destinations = json.load(f)

# Captcha bypass
def captcha_bypass(session, virtual_display=False):
    try:
        cookies = frontier_captcha_solver.get_cookies(virtual_display)
        for cookie in cookies["cookies"]:
            session.cookies.set(cookie['name'], cookie['value'])
        session.headers.update({"User-Agent": cookies["user_agent"]})
    except Exception as e:
        logging.warning("Failed to bypass captcha. Continuing without cookies. " + str(e))


def generate_user_agent():
    platform = random.choice(['Windows NT 10.0', 'Macintosh; Intel Mac OS X 10_15_7'])
    webkit_version = random.choice(['537.36', '605.1.15'])
    chrome_version = f"{random.randint(80, 91)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)}"
    firefox_version = f"{random.randint(80, 89)}.0"
    return f"Mozilla/5.0 ({platform}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}"

def _get_schedule_data(i, origin, date, dest, session, cj, cjs, header, retries=3):

    # Mimic human-like behavior by adding delays between requests
    time.sleep(random.uniform(0.5,0.75))

    schedule_url = f"https://booking.flyfrontier.com/Flight/RetrieveSchedule?calendarSelectableDays.Origin={origin}&calendarSelectableDays.Destination={dest}"
    schedule_response = session.get(schedule_url, headers=header, cookies=cj) if cjs else session.get(schedule_url, headers=header)
                
    if schedule_response.status_code == 200:
        schedule_data = schedule_response.json()
        disabled_dates = schedule_data['calendarSelectableDays']['disabledDates']
        last_available_date = schedule_data['calendarSelectableDays']['lastAvailableDate']

        # Convert the input date to the same format as the disabled dates list
        formatted_date = f'{date.month}/{date.day}/{date.year}'

        # Check if the date is in the list of disabled dates
        if formatted_date in disabled_dates or last_available_date == '0001-01-01 00:00:00':
            print(f"{i}. No flights available on {formatted_date} from {origin} to {dest}. Date skipped.")
            return False
    elif schedule_response.status_code == 403:
        logging.info("Captcha detected while getting schedule data. Attempting to bypass.")
        captcha_bypass(session)
        if retries > 1:
            return _get_schedule_data(i, origin, date, dest, session, cj, cjs, header, retries-1)
        else:
            raise Exception("Fatal error: Failed to bypass captcha.")
    else:
        raise Exception(f"Problem accessing URL: code {schedule_response.status_code}\n url = " + schedule_url)
    
    return True

def _get_flight_schedule_data(i, origin, date, dest, session, cj, cjs, header, retries=3):
    
    # Mimic human-like behavior by adding delays between requests
    time.sleep(random.uniform(0.5,0.75))

    date_str = date.strftime("%b-%d,-%Y").replace("-", "%20")
    url = f"https://booking.flyfrontier.com/Flight/InternalSelect?o1={origin}&d1={dest}&dd1={date_str}&ADT=1&mon=true&promo="
    response = session.get(url, headers=header, cookies=cj) if cjs else session.get(url, headers=header)
    
    if response.status_code == 200:
        return response
    elif response.status_code == 403:
        logging.info("Captcha detected while getting flight data. Attempting to bypass.")
        if retries > 1:
            captcha_bypass(session)
            return _get_flight_schedule_data(i, origin, date, dest, session, cj, cjs, header, retries-1)
        else:
            raise Exception("Fatal error: Failed to bypass captcha.")
    else:
        raise Exception(f"Problem accessing URL: code {response.status_code}\n url = " + url)

def get_flight_html(origin, date, session, cjs, roundtrip, start_index=0, destinations = all_destinations):
    global last_dest_added_id

    destination_keys = list(destinations.keys()) # Retrieve a list of destination keys
    for i in range(start_index, len(destination_keys)):
        dest = destination_keys[i]

        if dest == origin:
            print('cannot search between identical origin and destination')
            continue

        # Choose a random User-Agent header
        header = {
            "User-Agent": generate_user_agent(),
        } if cjs else {}
        cj = browsercookie.chrome() if cjs else None

        # Get schedule data for the route
        # and skip to next destination if not available
        if not _get_schedule_data(i, origin, date, dest, session, cj, cjs, header):
            continue

        # At this point, a flight should be available
        # Insert into Destination table if sqlite is enabled
        if conn and roundtrip != -1:
            c = conn.cursor()
            # Check if the destination already exists in the table
            c.execute("SELECT id FROM Destination WHERE dest_iata = ? AND from_iata = ? AND scrape_id = ?", (dest, origin, scrape_id))
            row = c.fetchone()
            if row:
                last_dest_added_id = row[0]
            else:
                c.execute("INSERT INTO Destination (scrape_id, dest_iata, from_iata, roundtrip_available, flight_count, total_fare) VALUES (?, ?, ?, ?, ?, ?)",
                          (scrape_id, dest, origin, False, 0, 0))
                conn.commit()
                last_dest_added_id = c.lastrowid

        # Get flight data for the route
        response = _get_flight_schedule_data(i, origin, date, dest, session, cj, cjs, header)
        decoded_data = extract_html(response)
        if (decoded_data != 'NoneType'):

            orgin_success = extract_json(decoded_data, origin, dest, date, roundtrip)
            if(roundtrip > 0 & orgin_success):
                new_dest = {origin: all_destinations[origin]}
                # 1 = trigger roundtrip
                # 0 = no roundtrip
                # -1 = in roundtrip recurssion 

                # Loop the amount of times specified by roundtrip
                # and call get_flight_html() with the new destination
                for i in range(1, roundtrip+1):
                    get_flight_html(dest, (date+timedelta(days=i)), session, cjs, -1, 0, new_dest)
                #roundtrip = 1 # reset var for the next dest
        else:
            print(f"Error: No data found for {origin} to {dest} on {date.strftime('%A, %m-%d-%y')}")

def _get_duration_seconds(list_of_durations):
    return reduce(lambda x, y: x + y, [int(h) * 3600 + int(m) * 60 + int(s) for h, m, s in (duration.split(":") for duration in list_of_durations)])

def _convert_duration_to_seconds(duration_string):
    days, hours, minutes = 0, 0, 0

    if "day" in duration_string:
        days, hours, minutes = map(int, re.findall(r'\d+', duration_string))
    else:
        hours, minutes = map(int, re.findall(r'\d+', duration_string))

    total_seconds = (days * 24 * 3600) + (hours * 3600) + (minutes * 60)
    return total_seconds

def extract_json(flight_data, origin, dest, date, roundtrip):
    # Extract the flights with isGoWildFareEnabled as true
    try:
        flights = flight_data['journeys'][0]['flights']
    except (TypeError, KeyError):
        return 0
    if (flights == None):
        return 0
    go_wild_count = 0

    for flight in flights:
        if flight["isGoWildFareEnabled"]:
            if (go_wild_count == 0):
                print(f"\n{'{} to {}: {}'.format(origin, dest, all_destinations[dest]['desc']) if roundtrip != -1 else '**Return flight'} available:")
                #print(f"\n{'{origin} to {dest}: {all_destinations[dest]}' if roundtrip!=-1 else 'Return flight'} available:")
            go_wild_count+=1
            info = flight['legs'][0]
            last = flight['legs'][-1]
            print(f"flight {go_wild_count}. {flight['stopsText']}")
            print(f"\tDate: {info['departureDate'][5:10]}")
            print(f"\tDepart: {info['departureDateFormatted']}")
            print(f"\tTotal flight time: {flight['duration']}")
            print(f"Price: ${flight['goWildFare']}")
            # if go wild seats value is provided
            if flight['goWildFareSeatsRemaining'] is not None:
                print(f"Go Wild: {flight['goWildFareSeatsRemaining']}\n")

            # Insert into Flight table if sqlite is enabled
            if conn:
                c = conn.cursor()
                c.execute("INSERT INTO Flight (dest_id, dest_iata, from_iata, stops_count, stops_airports, airport_time, flight_time, total_time, departure_time, arrival_time, fare, seats_remaining) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (
                            last_dest_added_id,
                            dest,
                            origin,
                            flight['stopCount'],
                            ','.join([stop['station'] for stop in flight['stops']]) if flight['stopCount'] > 0 else '',
                            _get_duration_seconds([stop['duration'] for stop in flight['stops']]) if flight['stopCount'] > 0 else 0,
                            _get_duration_seconds([leg['duration'] for leg in flight['legs']]),
                            _convert_duration_to_seconds(flight['duration']),
                            datetime.fromisoformat(info['departureDateUtc'].replace("Z", "+00:00")),
                            datetime.fromisoformat(last['arrivalDateUtc'].replace("Z", "+00:00")),
                            flight['goWildFare'],
                            int(re.findall(r'\d+', flight['goWildFareSeatsRemaining'])[0]) if flight['goWildFareSeatsRemaining'] is not None else None
                          ))
                
                # Update the destination table
                c.execute("UPDATE Destination SET flight_count = flight_count + 1, total_fare = total_fare + ? WHERE id = ?", (flight['goWildFare'], last_dest_added_id))
                conn.commit()
    
    if (go_wild_count == 0):
        print(f"No {'next day return ' if roundtrip==-1 else ''}flights from {origin} to {dest}")
        return 0
    else:
        if(roundtrip==-1):
            roundtrip_avail[origin] = all_destinations.get(origin)

            if conn:
                c = conn.cursor()
                c.execute("UPDATE Destination SET roundtrip_available = ? WHERE id = ?",(True, last_dest_added_id))
                conn.commit()
        else:
            destinations_avail[dest] = all_destinations.get(dest)
        print(f"{origin} to {dest}: {go_wild_count} GoWild {'return ' if roundtrip==-1 else''}flights available for {date.strftime('%A, %m-%d-%y')}")
    return 1

def extract_html(response):
    # Parse the HTML source using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all <script> tags with type="text/javascript" and extract their contents
    scripts = soup.find("script", type="text/javascript")
    decoded_data = html.unescape(scripts.text)
    decoded_data = decoded_data[decoded_data.index('{'):decoded_data.index(';')-1]
    return json.loads(decoded_data)

def print_dests(origin):
    print(json.dumps(destinations_avail, indent=4, sort_keys=True))
    print(f"\n{len(destinations_avail)} destinations found from {origin}:")
    for dest, name in destinations_avail.items():
        print(f"{'**' if dest in roundtrip_avail else ''}{dest}: {name}")
    print("** = next day return flight available")

def main():
    global all_destinations

    parser = argparse.ArgumentParser(description='Check flight availability.')
    parser.add_argument('-o', '--origin', type=str, required=True, help='Origin IATA airport code.')
    # New! can search any date now
    parser.add_argument('-d', '--dates', type=int, required=True, help='Show flights for:\n\tToday: 0\n\tTommorrow: 1\n\tAny number of days past today: ')
    # ??? testing how to offer feature right now
    parser.add_argument('-t', '--roundtrip', type=int, default=0, help='Search for a roundtrip/return flights N days in the future. 1=Only next day return flights, 2=Plus the next day, so forth.')
    parser.add_argument('-c', '--cjs', action='store_true', help='Use browser cookies.')
    parser.add_argument('-r', '--resume', type=int, default=0, help='Index of airport to resume from. Use index 21 to only search for contiguous US destinations.')

    # Captcha related args
    parser.add_argument('--captcha-solver', action='store_true', help='Use captcha solver (experimental).')
    parser.add_argument('--virtual-display', action='store_true', help='Use virtual display with the captcha solver (experimental).')

    parser.add_argument('--store-sqlite', action='store_true', help='Use sqlite3 database to store results.')

    args = parser.parse_args()
    origin = args.origin.upper()
    input_dates = args.dates
    #roundtrip = args.roundtrip()
    cjs = args.cjs
    #fly_date = datetime.today() + timedelta(days=input_dates) # Searches date of today + input 
    fly_dates = [datetime.today() + timedelta(days=i) for i in range(input_dates+1)]
    session = requests.Session()
    resume = args.resume
    roundtrip = args.roundtrip
    captcha_solver = args.captcha_solver
    virtual_display = args.virtual_display
    sqlite = args.store_sqlite

    # Setup sqlite if needed
    if sqlite:
        global conn
        global scrape_id

        import sqlite3
        conn = sqlite3.connect('gowild.db')
        c = conn.cursor()
        # Check if table exists
        c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='Scrape' ''')
        if c.fetchone()[0]==1 :
            logging.info('Table exists.')
        else:
            logging.info('Table does not exist. Creating...')
            # Use the tables.sql file to create the table
            with open('tables.sql', 'r') as f:
                c.executescript(f.read())
            logging.info('Table created.')

        # Add a scrape entry
        c.execute("INSERT INTO Scrape (scrape_time, success) VALUES (?, ?)",
                  (datetime.now(), False))
        conn.commit()

        # Get the ID of the scrape entry
        scrape_id = c.lastrowid

    # captcha bypass
    if captcha_solver:
        captcha_bypass(session, virtual_display)

    print(f"\nFlights for {','.join([fly_date.strftime('%A, %m-%d-%y') for fly_date in fly_dates])}:")
    
    for i, fly_date in enumerate(fly_dates):
        get_flight_html(origin, fly_date, session, cjs, 0 if i>0 else roundtrip, resume)
    
    print_dests(origin)

    # Close sqlite connection
    if conn:
        c = conn.cursor()
        c.execute("UPDATE Scrape SET success = ? WHERE id = ?", (True, scrape_id))
        conn.commit()
        conn.close()

if __name__ == "__main__":

    # Set log level
    logging.basicConfig(level=logging.INFO)

    main()
