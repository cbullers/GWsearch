<script setup lang="ts">

import {computed, ref} from 'vue'
import {useFlightStore} from "@/stores/flights";
import {Scrape} from "@/api";

const store = useFlightStore();
const scrape = ref(null as any);

await store.loadScrapes();

const loadScrape = (scrape: Scrape) => {
  store.loadScrape(scrape.id);
}

// find most recent scrape
const recent = store.scrapes.reduce((prev, current) => (prev.scrape_time > current.scrape_time) ? prev : current);
loadScrape(recent);
scrape.value = recent;

</script>

<template>

  <div class="full-width flex justify-center" style="position:sticky;top:0;z-index:999;">
    <q-toolbar class="bg-green-5 text-white shadow-2">
      <q-btn flat label="GWsearch" />
      <q-space />
      <q-toolbar-title>From: {{ store.origin }}</q-toolbar-title>
      
      
      <div class="flex justify-center items-center" style="gap:.2rem;">
<!--        <q-toolbar-title>Selected Scrape</q-toolbar-title>-->
        <q-select
          v-model="scrape"
          :options="store.scrapes"
          :option-value="option => option.id"
          :option-label="option => new Date(option.scrape_time).toLocaleString()"
          @update:model-value="loadScrape"
          class="text-white"
          style="min-width: 200px;"
        />
      </div>
      
    </q-toolbar>
  </div>

</template>

<style scoped>

</style>
