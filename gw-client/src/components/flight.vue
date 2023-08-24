<script setup lang="ts">

import {defineProps, ref} from "vue";
import type {Flight} from "@/api";
import moment from "moment";

const props = defineProps<{
  flight: Flight,
  selected: boolean,
}>();

</script>

<template>

  <q-toolbar class="bg-grey-2 shadow-2 flex wrap justify-between">

    <q-checkbox :model-value="props.selected" @update:model-value="$emit('selected')" />

    <q-chip square color="grey-4" icon="arrow_upward" class="col-grow">
      {{ new Date(props.flight.departure_time).toLocaleString() }}
    </q-chip>

    <q-chip square color="grey-4" icon="hourglass_empty" v-if="props.flight.stops_count > 0" class="col-grow">
      {{ props.flight.stops_airports }} for {{ moment.duration(props.flight.airport_time*1000).humanize() }}
    </q-chip>

    <q-chip square color="grey-4" icon="arrow_downward" class="col-grow">
      {{ new Date(props.flight.arrival_time).toLocaleString() }}
    </q-chip>

    <q-chip square color="grey-4" icon="schedule" class="col-grow">
      {{ moment.duration(props.flight.total_time*1000).humanize() }}
    </q-chip>

    <q-chip square color="green-2" icon="attach_money" class="col-grow">
      {{ props.flight.fare }}
    </q-chip>

    <q-chip square color="purple-2" icon="airline_seat_recline_normal" v-if="props.flight.seats_remaining" class="col-grow">
      {{ props.flight.seats_remaining }} seats remaining
    </q-chip>

  </q-toolbar>

</template>

<style scoped>

</style>
