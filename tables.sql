CREATE TABLE Scrape (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    scrape_time DATETIME NOT NULL,
    success BOOLEAN NOT NULL
);

CREATE TABLE Destination (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    scrape_id INTEGER NOT NULL,
    dest_iata TEXT NOT NULL,
    from_iata TEXT NOT NULL,
    roundtrip_available BOOLEAN NOT NULL,
    flight_count INTEGER NOT NULL,
    total_fare DECIMAL NOT NULL,
    FOREIGN KEY (scrape_id) REFERENCES Scrape(id)
);

CREATE TABLE Flight (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    dest_id INTEGER NOT NULL,
    dest_iata TEXT NOT NULL,
    from_iata TEXT NOT NULL,
    stops_count INTEGER NOT NULL,
    stops_airports TEXT NOT NULL,
    airport_time INTEGER NOT NULL,
    flight_time INTEGER NOT NULL,
    total_time INTEGER NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    fare DECIMAL NOT NULL,
    seats_remaining INTEGER NULL,
    FOREIGN KEY (dest_id) REFERENCES Destination(id)
);