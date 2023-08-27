<script setup lang="ts">

import {computed, ref} from 'vue';
import navigation from '@/components/navigation.vue';
import {useFlightStore} from "@/stores/flights";

import destinations from '@/destinations';
import type {Destination} from "@/api";
import moment from "moment";
import FlightView from "@/components/flight.vue";
import type {Flight} from "@/api";

const store = useFlightStore();

const filters = ref({
  roundtrip: true,
  desiredDeparture: null as any,
  desiredReturn: null as any,
  sortBy: 'Location Time',
  sort: 'desc',
  minimumLocationTimeHours: 4,
})

const sorts = [
  'Location Time',
  'Total Flights',
    'Travel Time',
    'Round-Trip Flights',
    'Fare'
]

const dests = computed(() => {
  
  return store.selectedScrape?.destinations.map(d => {
    const {flights, ...rest} = d;
    return {
      ...rest,
      flights: flights.filter(f => {
        // filter out flights that arrive later than desired return date
        return ((!filters.value.desiredReturn || (new Date(f.arrival_time).setHours(0,0,0,0) <= new Date(filters.value.desiredReturn).setHours(0,0,0,0))))
            && ((!filters.value.desiredDeparture || (new Date(f.departure_time).setHours(0,0,0,0) >= new Date(filters.value.desiredDeparture).setHours(0,0,0,0))))
            && (!(filters.value.minimumLocationTimeHours && (getLongestTimeInLocation(d, false) as number < filters.value.minimumLocationTimeHours*60*60*1000)))
      })
    }
  })
  
})

const filteredDestinations = computed(() => {
  if(!store.selectedScrape || !store.selectedScrape.destinations)
    return [];
  
  return dests.value?.filter(dest => {
    return !(filters.value.roundtrip && !dest.roundtrip_available) && (getLongestTimeInLocation(dest, false) as number > 0);
  }).filter(dest => dest.flights.filter(f => f.from_iata === store.origin).length > 0)
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
  &o2=${r?.from_iata}&d2=${r?.dest_iata}&dd2=${returnDate}&mon=true&umnr=false&ADT=1`;
  
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
  return (destinations as any)[dest];
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
            <div class="flex justify-between no-wrap items-center" style="gap:1rem;">
              <span><strong>{{dest.dest_iata}}</strong> | {{getDestName(dest.dest_iata)}}</span>
              <div class="flex justify-end" style="gap:.2rem;">
                <q-chip square color="primary" text-color="white" icon="event" size="sm">
                  {{ dest.flights.length }} total flights
                </q-chip>
                <q-chip v-if="dest.roundtrip_available" square color="green" text-color="white" icon="check" size="sm">
                  Round-Trip (x{{ getReturnFlightCount(dest) }})
                </q-chip>
                <q-chip square color="secondary" text-color="white" icon="airplane_ticket" size="sm">
                  {{ getShortestTravelTime(dest) }}
                </q-chip>
                <q-chip square color="accent" text-color="white" icon="location_on" size="sm">
                  {{ getLongestTimeInLocation(dest) }}
                </q-chip>
                <q-chip square color="green-8" text-color="white" icon="attach_money" size="sm">
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
    <q-toolbar class="bg-green-4 shadow-2 flex justify-center items-center">

      <q-chip clickable square color="red-5" text-color="white" @click="() => {selectedReturn=null;selectedDeparture=null;}">
        Clear
      </q-chip>
      
      <q-chip square color="blue-9" text-color="white">
        Destination: {{ selectedDeparture.dest_iata }} | {{ getDestName(selectedDeparture.dest_iata) }}
      </q-chip>

      <q-chip square color="blue-9" text-color="white">
        Layovers: {{ moment.duration((selectedReturn.airport_time + selectedDeparture.airport_time)*1000).humanize() }}
      </q-chip>

      <q-chip square color="blue-9" text-color="white">
        Total Travel Time: {{ moment.duration((selectedReturn.total_time + selectedDeparture.total_time)*1000).humanize() }}
      </q-chip>

      <q-chip square color="blue-9" text-color="white">
        Time In Location: {{ moment.duration(moment(selectedDeparture.arrival_time).diff(moment(selectedReturn.departure_time))).humanize() }}
      </q-chip>

      <q-chip square color="blue-9" text-color="white">
        Cost: ${{ (selectedReturn.fare + selectedDeparture.fare).toFixed(2) }}
      </q-chip>

      <q-chip clickable square color="yellow-6" @click="bookFlight">
        Book
      </q-chip>

    </q-toolbar>
  </div>

</template>

<style scoped>

</style>
