<script setup lang="ts">

import {computed, ref} from 'vue';
import navigation from '@/components/navigation.vue';
import {useFlightStore} from "@/stores/flights";

import destinations from '@/destinations';
import type {Destination} from "@/api";
import moment from "moment-timezone";
import FlightView from "@/components/flight.vue";
import type {Flight} from "@/api";
import {API} from "@/api";

const store = useFlightStore();

const filters = ref({
  roundtrip: true,
  desiredDeparture: null as any,
  desiredReturn: null as any,
  sortBy: 'Sunlight Hours',
  sort: 'desc',
  numAdults: 2,
  minimumLocationTimeHours: 4,
})

const sorts = [
  'Location Time',
    'Sunlight Hours',
  'Total Flights',
    'Travel Time',
    'Round-Trip Flights',
    'Fare'
]

const mobile = ref(false);
mobile.value = window.innerWidth < 768;

const dests = computed(() => {
  
  return store.selectedScrape?.destinations.map(d => {
    const {flights, ...rest} = d;
    return {
      ...rest,
      flights: flights.filter(f => {
        // filter out flights that arrive later than desired return date
        return ((!filters.value.desiredReturn || (new Date(f.arrival_time).setHours(0,0,0,0) <= new Date(filters.value.desiredReturn).setHours(0,0,0,0))))
            && ((!filters.value.desiredDeparture || (new Date(f.departure_time).setHours(0,0,0,0) >= new Date(filters.value.desiredDeparture).setHours(0,0,0,0))))
      })
    }
  })
  
})

const filteredDestinations = computed(() => {
  if(!store.selectedScrape || !store.selectedScrape.destinations)
    return [];
  
  return dests.value?.filter(dest => {
    return !(filters.value.roundtrip && !dest.roundtrip_available) && (getLongestTimeInLocation(dest, false) as number > 0);
  }).filter(dest =>
  {
    return dest.flights.filter(f => f.from_iata === store.origin).length > 0
      && (!(filters.value.minimumLocationTimeHours && (getLongestTimeInLocation(dest, false) as number < filters.value.minimumLocationTimeHours*60*60*1000)))
  })
      .sort((a:Destination, b:Destination) => {

        switch(filters.value.sortBy)
        {
          case 'Location Time':
            return (filters.value.sort === 'asc') ? getLongestTimeInLocation(a, false) > getLongestTimeInLocation(b, false) ? 1 : -1 : getLongestTimeInLocation(a, false) < getLongestTimeInLocation(b, false) ? 1 : -1;
          case 'Total Flights':
            return (filters.value.sort === 'asc') ? a.flights.length > b.flights.length ? 1 : -1 : a.flights.length < b.flights.length ? 1 : -1;
          case 'Round-Trip Flights':
            return (filters.value.sort === 'asc') ? getReturnFlightCount(a) > getReturnFlightCount(b) ? 1 : -1 : getReturnFlightCount(a) < getReturnFlightCount(b) ? 1 : -1;
          case 'Travel Time':
            return (filters.value.sort === 'asc') ? (getShortestTravelTime(a,false) > getShortestTravelTime(b,false) ? 1 : -1) : (getShortestTravelTime(a,false) < getShortestTravelTime(b,false) ? 1 : -1);
          case 'Fare':
            return (filters.value.sort === 'asc') ? getCheapestJourney(a, false) > getCheapestJourney(b, false) ? 1 : -1 : getCheapestJourney(a, false) < getCheapestJourney(b, false) ? 1 : -1;
          case 'Sunlight Hours':
            return (filters.value.sort === 'asc') ? (getLongestSunlightHoursInLocation(a,false) > getLongestSunlightHoursInLocation(b,false) ? 1 : -1) : (getLongestSunlightHoursInLocation(a,false) < getLongestSunlightHoursInLocation(b,false) ? 1 : -1);
        }
        return 0;
      })
})

const selectedDeparture = ref<Flight | null>(null);
const selectedReturn = ref<Flight | null>(null);

const bookFlight = () => {
  
  if(!selectedDeparture.value || !selectedReturn.value)
    return;
  
  const d = selectedDeparture.value;
  const departDate = new Date(d?.departure_time).toLocaleDateString();
  
  const r = selectedReturn.value;
  const returnDate = new Date(r?.departure_time).toLocaleDateString();
  
  const url = `https://booking.flyfrontier.com/Flight/InternalSelect?o1=${d?.from_iata}&d1=${d?.dest_iata}&dd1=${departDate}
  &o2=${r?.from_iata}&d2=${r?.dest_iata}&dd2=${returnDate}&mon=true&umnr=false&ADT=${filters.value.numAdults}`;
  
  window.open(url, '_blank');
  
}

const nearestHalfHour = (date: moment.Moment) => {
  const minutes = date.minutes();
  if(minutes < 15)
    return date.minutes(0).seconds(0);
  else if(minutes < 45)
    return date.minutes(30).seconds(0);
  else
    return date.minutes(0).seconds(0).add(1,'hours');
}
const findCar = () => {

  if(!selectedDeparture.value || !selectedReturn.value)
    return;

  const d = selectedDeparture.value;
  const arriveDate = nearestHalfHour(moment(d?.arrival_time)).tz(getDestTz(d?.dest_iata)).format('YYYYMMDD-HH:mm');

  const r = selectedReturn.value;
  const returnDate = nearestHalfHour(moment(r?.departure_time)).tz(getDestTz(r?.from_iata)).subtract(1,'hours').format('YYYYMMDD-HH:mm');
  
  const url = `https://www.priceline.com/drive/search/r/listings/${d?.dest_iata}/${d?.dest_iata}/${arriveDate}/${returnDate}/list?driverAge=21&listSortBy=TOTAL_PRICE`;
  
  window.open(url, '_blank');
}

const findHotel = () => {
  
    if(!selectedDeparture.value || !selectedReturn.value)
      return;
  
    const d = selectedDeparture.value;
    const arriveDate = moment(d?.arrival_time).tz(getDestTz(d?.dest_iata)).format('YYYYMMDD');
  
    const r = selectedReturn.value;
    const returnDate = moment(r?.departure_time).tz(getDestTz(r?.from_iata)).format('YYYYMMDD');
  
    const url = `https://www.priceline.com/relax/in/${d?.dest_iata}/from/${arriveDate}/to/${returnDate}/rooms/1/adults/${filters.value.numAdults}?sortby=PRICE`;
    
    window.open(url, '_blank');
}

const findHotelCarCombo = async () => {

  if(!selectedDeparture.value || !selectedReturn.value)
    return;
  
  const url = await API.getPricelineCombo(selectedDeparture.value.id, selectedReturn.value.id, filters.value.numAdults);
  
  window.open(url, '_blank');
}

const getReturnFlightCount = (dest: Destination) =>
{
  return dest.flights.filter(f => f.dest_iata === store.origin).length;
}

const getShortestTravelTime = (dest: Destination, human=true) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin);
  const arrivals = dest.flights.filter(f => f.dest_iata === store.origin);
  
  if(departures.length === 0 || arrivals.length === 0)
    return 0;
  
  const shortestDeparture = departures.reduce((prev, current) => (prev.total_time < current.total_time) ? prev : current);
  const shortestArrival = arrivals.reduce((prev, current) => (prev.total_time < current.total_time) ? prev : current);
  
  if(shortestDeparture.total_time + shortestArrival.total_time === 0)
    return 0;
  moment.relativeTimeThreshold('h', 1000);
  let duration = moment.duration((shortestDeparture.total_time + shortestArrival.total_time)*1000)
  return human ? duration.humanize() : duration.asMilliseconds();
}


const getLongestTimeInLocation = (dest: Destination, human=true) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin);
  const arrivals = dest.flights.filter(f => f.dest_iata === store.origin);
  
  if(departures.length === 0 || arrivals.length === 0)
    return 0;
  
  const earliestDepartureArrival = departures.reduce((prev, current) => (new Date(prev.arrival_time) < new Date(current.arrival_time)) ? prev : current);
  const latestArrivalDeparture = arrivals.reduce((prev, current) => (new Date(prev.departure_time) > new Date(current.departure_time)) ? prev : current);
  
  moment.relativeTimeThreshold('h', 1000);
  let duration = moment.duration((new Date(latestArrivalDeparture.departure_time).getTime() - new Date(earliestDepartureArrival.arrival_time).getTime()));
  return human ? duration.humanize() : duration.asMilliseconds();
}

function calculateSunlightHours(departure: any, arrival: any) {
  const MS_IN_HOUR = 1000 * 60 * 60;
  const SUNLIGHT_START_HOUR = 6;
  const SUNLIGHT_END_HOUR = 18;

  let totalSunlightHours = 0;
  let current = new Date(departure) as any;

  while (current < arrival) {
    let nextDay = new Date(current) as any;
    nextDay.setHours(24, 0, 0, 0);

    let sunlightStart = new Date(current).setHours(SUNLIGHT_START_HOUR, 0, 0, 0);
    let sunlightEnd = new Date(current).setHours(SUNLIGHT_END_HOUR, 0, 0, 0);

    let actualStart = Math.max(current, sunlightStart);
    let actualEnd = Math.min(nextDay, arrival, sunlightEnd);

    if (actualEnd > actualStart) {
      totalSunlightHours += (actualEnd - actualStart) / MS_IN_HOUR;
    }

    current = nextDay;
  }

  return totalSunlightHours;
}


const getLongestSunlightHoursInLocation = (dest: Destination, human=true) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin).map(f => moment(f.arrival_time).tz(getDestTz(f.dest_iata)).toDate().getTime());
  const returns = dest.flights.filter(f => f.dest_iata === store.origin).map(f => moment(f.departure_time).tz(getDestTz(f.from_iata)).toDate().getTime());
  
  if(departures.length === 0 || returns.length === 0)
    return 0;

  let maxSunlightHours = 0;

  departures.forEach(departure => {
    returns.forEach(returnTime => {
      if (returnTime > departure) {
        let sunlightHours = calculateSunlightHours(departure, returnTime);
        maxSunlightHours = Math.max(maxSunlightHours, sunlightHours);
      }
    });
  });
  
  moment.relativeTimeThreshold('h', 1000);
  let duration = moment.duration(maxSunlightHours, 'hours');
  return human ? duration.humanize() : duration.asMilliseconds();
}

const getCheapestJourney = (dest: Destination, human=true) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin);
  const arrivals = dest.flights.filter(f => f.dest_iata === store.origin);
  
  if(departures.length === 0 || arrivals.length === 0)
    return 0;
  
  const cheapestDeparture = departures.reduce((prev, current) => (prev.fare < current.fare) ? prev : current);
  const cheapestArrival = arrivals.reduce((prev, current) => (prev.fare < current.fare) ? prev : current);
  
  return human ? (cheapestDeparture.fare + cheapestArrival.fare).toFixed(2) : (cheapestDeparture.fare + cheapestArrival.fare);
}

const getDestName = (dest: string) => {
  return (destinations as any)[dest]['desc'];
}
const getDestTz = (dest: string) => {
  return (destinations as any)[dest]['tz'];
}

</script>

<template>
  
  <navigation />

  <div class="full-width flex justify-center">
    <q-toolbar class="bg-grey-2 shadow-2 flex q-pa-sm" style="gap:.5rem;flex-wrap: wrap!important;">
      

      <q-field filled square stack-label dense class="col-grow" borderless readonly>
        <template v-slot:control>
          <q-checkbox v-model="filters.roundtrip" label="Round-Trip Only" dense />
        </template>
      </q-field>
      
      <q-input filled v-model="filters.desiredDeparture" mask="##/##/####" class="col-grow" square hide-bottom-space dense label="Desired Departure">
        <template v-slot:append>
          <q-icon name="event" class="cursor-pointer">
            <q-popup-proxy cover transition-show="scale" transition-hide="scale">
              <q-date v-model="filters.desiredDeparture" mask="MM/DD/YYYY">
                <div class="row items-center justify-end">
                  <q-btn v-close-popup label="Close" color="primary" flat />
                </div>
              </q-date>
            </q-popup-proxy>
          </q-icon>
        </template>
      </q-input>
      
      <q-input filled v-model="filters.desiredReturn" mask="##/##/####" class="col-grow" square hide-bottom-space dense label="Desired Return">
        <template v-slot:append>
          <q-icon name="event" class="cursor-pointer">
            <q-popup-proxy cover transition-show="scale" transition-hide="scale">
              <q-date v-model="filters.desiredReturn" mask="MM/DD/YYYY">
                <div class="row items-center justify-end">
                  <q-btn v-close-popup label="Close" color="primary" flat />
                </div>
              </q-date>
            </q-popup-proxy>
          </q-icon>
        </template>
      </q-input>

      <q-input filled v-model="filters.minimumLocationTimeHours" class="col-grow" square hide-bottom-space dense label="Min Loc Time (Hrs)" />

      <q-input filled v-model="filters.numAdults" class="col-grow" square hide-bottom-space dense label="# of Travelers" />

      <q-select
          v-model="filters.sortBy"
          :options="sorts"
          class="col-grow"
          dense
          filled
          square
          label="Sort"
      />
      <div>
        <q-avatar icon="arrow_upward" dense :text-color="filters.sort==='asc' ? 'black' : 'grey'" rounded icon-right class="cursor-pointer" @click="filters.sort='asc'" />
        <q-avatar icon="arrow_downward" dense :text-color="filters.sort==='desc' ? 'black' : 'grey'" rounded icon-right class="cursor-pointer" @click="filters.sort='desc'"  />
      </div>

    </q-toolbar>
  </div>
  
  <q-list bordered v-if="store.selectedScrape && store.selectedScrape.destinations">
    
    <template v-for="dest in filteredDestinations">
      <q-expansion-item
          group="flightgroup"
          icon="flight"
          :label="dest.dest_iata"
          header-class="text-primary"
      >
        <template v-slot:header>
          <q-item-section>
            <div class="flex justify-between no-wrap items-center" style="gap:0.5rem;">
              <span><strong>{{dest.dest_iata}}</strong> | {{getDestName(dest.dest_iata)}}</span>
              <div class="flex justify-end" style="gap:.05rem;">
                <q-chip square color="primary" text-color="white" icon="event" size="sm">
                  <q-tooltip>Total Count Of Flights</q-tooltip>
                  {{ dest.flights.length }} flights
                </q-chip>
                <q-chip v-if="dest.roundtrip_available" square color="green" text-color="white" icon="check" size="sm">
                  <q-tooltip>Total Return Flight Count</q-tooltip>
                  Returns (x{{ getReturnFlightCount(dest) }})
                </q-chip>
                <q-chip square color="secondary" text-color="white" icon="airplane_ticket" size="sm">
                  <q-tooltip>Shortest Travel Time Combination</q-tooltip>
                  {{ getShortestTravelTime(dest) }}
                </q-chip>
                <q-chip square color="accent" text-color="white" icon="location_on" size="sm">
                  <q-tooltip>Longest Time In Location Combination</q-tooltip>
                  {{ getLongestTimeInLocation(dest) }}
                </q-chip>
                <q-chip square color="yellow" text-color="black" icon="wb_sunny" size="sm">
                  <q-tooltip>Longest Sunlight Hours In Location Combination (6a-6p)</q-tooltip>
                  {{ getLongestSunlightHoursInLocation(dest) }}
                </q-chip>
                <q-chip square color="green-8" text-color="white" icon="attach_money" size="sm">
                  <q-tooltip>Cheapest Journey Combination</q-tooltip>
                  {{ getCheapestJourney(dest) }}
                </q-chip>
              </div>
            </div>
            
          </q-item-section>
          

<!--          <q-item-section side>-->
<!--            <div class="row items-center">-->
<!--              <q-icon name="star" color="red" size="24px" />-->
<!--              <q-icon name="star" color="red" size="24px" />-->
<!--              <q-icon name="star" color="red" size="24px" />-->
<!--            </div>-->
<!--          </q-item-section>-->
        </template>
        
        <q-card>
          <q-card-section class="q-pa-none bg-light-blue-2">
            
            <q-toolbar class="bg-blue-2">
              <q-toolbar-title>Departures</q-toolbar-title>
            </q-toolbar>
              
            <flight-view :flight="flight" :selected="selectedDeparture === flight"
                         v-for="flight in dest.flights.filter(f => f.from_iata === store.origin)"
                          @selected="selectedDeparture = flight"
            />

            <q-toolbar class="bg-blue-2">
              <q-toolbar-title>Arrivals</q-toolbar-title>
            </q-toolbar>

            <flight-view :flight="flight" :selected="selectedReturn === flight"
                         v-for="flight in dest.flights.filter(f => f.dest_iata === store.origin)"
                          @selected="selectedReturn = flight"
            />
            
            
          </q-card-section>
        </q-card>
      </q-expansion-item>
  
      <q-separator />
    </template>
  </q-list>

  <div class="full-width flex justify-center" style="position:sticky;bottom:0;" v-if="selectedReturn && selectedDeparture">
    <q-toolbar class="bg-green-4 shadow-2 flex justify-center items-center column q-pa-sm">

      <div class="flex justify-center" style="gap:.2rem;">

        <q-chip clickable color="red-5" text-color="white" @click="() => {selectedReturn=null;selectedDeparture=null;}">
          Clear
        </q-chip>

        <q-chip clickable color="blue-grey-6" text-color="white" @click="bookFlight">
          <q-tooltip>Navigate to FlyFrontier</q-tooltip>
          Book Flight
        </q-chip>

        <q-chip clickable color="blue-grey-6" text-color="white" @click="findCar">
          <q-tooltip>Find a car through Priceline</q-tooltip>
          Find Car
        </q-chip>

        <q-chip clickable color="blue-grey-6" text-color="white" @click="findHotel">
          <q-tooltip>Find a hotel room through Priceline</q-tooltip>
          Find Hotel
        </q-chip>

        <q-chip clickable color="blue-grey-6" text-color="white" @click="findHotelCarCombo">
          <q-tooltip>Find a hotel room/car combo through Priceline</q-tooltip>
          Find Hotel+Car Combo
        </q-chip>

      </div>
      
      <q-separator class="full-width q-ma-xs" />
      
      <div class="flex justify-center" style="gap:.2rem;">
        <q-chip square color="blue-9" text-color="white" icon="explore">
          <q-tooltip>Destination</q-tooltip>
          {{ selectedDeparture.dest_iata }} | {{ getDestName(selectedDeparture.dest_iata) }}
        </q-chip>

        <q-chip square color="grey-8" text-color="white" icon="airline_stops">
          <q-tooltip>Layover Time</q-tooltip>
          {{ moment.duration((selectedReturn.airport_time + selectedDeparture.airport_time)*1000).humanize() }}
        </q-chip>

        <q-chip square color="secondary" text-color="white" icon="airplane_ticket">
          <q-tooltip>Total Travel Time</q-tooltip>
          {{ moment.duration((selectedReturn.total_time + selectedDeparture.total_time)*1000).humanize() }}
        </q-chip>

        <q-chip square color="accent" text-color="white" icon="location_on">
          <q-tooltip>Total Time In Location</q-tooltip>
          {{ moment.duration(moment(selectedDeparture.arrival_time).diff(moment(selectedReturn.departure_time))).humanize() }}
        </q-chip>

        <q-chip square color="yellow" text-color="black" icon="wb_sunny">
          <q-tooltip>Total Sunlight Hours In Location (6a-6p)</q-tooltip>
          {{ moment.duration(calculateSunlightHours(moment(selectedDeparture.arrival_time).tz(getDestTz(selectedDeparture.dest_iata)).toDate().getTime()
            , moment(selectedReturn.departure_time).tz(getDestTz(selectedReturn.from_iata)).toDate().getTime()), 'hours').humanize() }}
        </q-chip>

        <q-chip square color="green-8" text-color="white" icon="attach_money">
          <q-tooltip>Total Cost</q-tooltip>
          {{ (selectedReturn.fare + selectedDeparture.fare).toFixed(2) }}
        </q-chip>

      </div>

    </q-toolbar>
  </div>

</template>

<style scoped>

</style>
