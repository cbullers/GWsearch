export interface Scrape {
    id: number;
    scrape_time: Date;
    success: boolean;
    destinations: Destination[];
}

export interface Destination {
    id: number;
    scrape_id: number;
    dest_iata: string;
    from_iata: string;
    roundtrip_available: boolean;
    flight_count: number;
    total_fare: number;
    flights: Flight[];
}

export interface Flight {
    id: number;
    dest_id: number;
    dest_iata: string;
    from_iata: string;
    stops_count: number;
    stops_airports: string;
    airport_time: number;
    flight_time: number;
    total_time: number;
    departure_time: Date;
    arrival_time: Date;
    fare: number;
    seats_remaining: number | null;
}

export class API 
{

    private static readonly BASE_URL =
        window.location.href.indexOf('localhost') > 0
        ? 'http://localhost:42345/api'
            : '/api';
        
    public static async getScrape(id: number): Promise<Scrape> 
    {
        const response = await fetch(`${this.BASE_URL}/scrapes/${id}`);
        const scrape = await response.json();
        return scrape['scrape'];
    }

    public static async getScrapes(): Promise<Scrape[]> 
    {
        const response = await fetch(`${this.BASE_URL}/scrapes`);
        const scrapes = await response.json();
        return scrapes['scrapes'];
    }

}