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
})

const filteredDestinations = computed(() => {
  if(!store.selectedScrape || !store.selectedScrape.destinations)
    return [];
  
  return store.selectedScrape.destinations.filter(dest => {
    return !(filters.value.roundtrip && !dest.roundtrip_available);
  }).filter(dest => dest.flights.filter(f => f.from_iata === store.origin).length > 0);
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

const getShortestTravelTime = (dest: Destination) =>
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
  return duration.humanize();
}


const getLongestTimeInLocation = (dest: Destination) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin);
  const arrivals = dest.flights.filter(f => f.dest_iata === store.origin);
  
  if(departures.length === 0 || arrivals.length === 0)
    return 0;
  
  const earliestDepartureArrival = departures.reduce((prev, current) => (new Date(prev.arrival_time) < new Date(current.arrival_time)) ? prev : current);
  const latestArrivalDeparture = arrivals.reduce((prev, current) => (new Date(prev.departure_time) > new Date(current.departure_time)) ? prev : current);
  
  moment.relativeTimeThreshold('h', 1000);
  let duration = moment.duration((new Date(latestArrivalDeparture.departure_time).getTime() - new Date(earliestDepartureArrival.arrival_time).getTime()));
  return duration.humanize();
}

const getCheapestJourney = (dest: Destination) =>
{
  const departures = dest.flights.filter(f => f.from_iata === store.origin);
  const arrivals = dest.flights.filter(f => f.dest_iata === store.origin);
  
  if(departures.length === 0 || arrivals.length === 0)
    return 0;
  
  const cheapestDeparture = departures.reduce((prev, current) => (prev.fare < current.fare) ? prev : current);
  const cheapestArrival = arrivals.reduce((prev, current) => (prev.fare < current.fare) ? prev : current);
  
  return (cheapestDeparture.fare + cheapestArrival.fare).toFixed(2);
}

</script>

<template>
  
  <navigation />

  <div class="full-width flex justify-center">
    <q-toolbar class="bg-grey-2 shadow-2">

      <q-checkbox v-model="filters.roundtrip" label="Round-Trip Only" />

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
          <q-item-section avatar>
            <q-avatar icon="flight"  />
          </q-item-section>

          <q-item-section>
            {{dest.dest_iata}} | {{destinations[dest.dest_iata]}}
          </q-item-section>
          
          <q-item-section side>
            <div class="flex" style="gap:.2rem;">
              <q-chip square color="primary" text-color="white" icon="event">
                {{ dest.flights.length }} total flights
              </q-chip>
              <q-chip v-if="dest.roundtrip_available" square color="green" text-color="white" icon="check">
                Round-Trip (x{{ getReturnFlightCount(dest) }})
              </q-chip>
              <q-chip square color="secondary" text-color="white" icon="airplane_ticket">
                {{ getShortestTravelTime(dest) }}
              </q-chip>
              <q-chip square color="accent" text-color="white" icon="location_on">
                {{ getLongestTimeInLocation(dest) }}
              </q-chip>
              <q-chip square color="green-8" text-color="white" icon="attach_money">
                {{ getCheapestJourney(dest) }}
              </q-chip>
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
        Destination: {{ selectedDeparture.dest_iata }} | {{ destinations[selectedDeparture.dest_iata] }}
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
