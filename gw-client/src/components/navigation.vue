<script setup lang="ts">

import {computed, ref} from 'vue'
import {useFlightStore} from "@/stores/flights";
import type {Scrape} from "@/api";
import destinations from "@/destinations";

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

const getDestName = (dest: string) => {
  return (destinations as any)[dest];
}

</script>

<template>

  <div class="full-width flex justify-center" style="position:sticky;top:0;z-index:999;">
    <q-toolbar class="bg-green-5 text-white shadow-2 flex justify-between">
      <q-btn flat label="GWsearch" />
      <q-btn flat :label="'FROM: ' + store.origin + ' | ' + getDestName(store.origin)" />
      
      
      <div class="flex justify-center items-center" style="gap:.2rem;">
<!--        <q-toolbar-title>Selected Scrape</q-toolbar-title>-->
        <q-chip square dense color="red" text-color="white" v-if="!store.selectedScrape?.success">
          Scrape Incomplete/Invalid
        </q-chip>
        <q-select
          v-model="scrape"
          dense
          :options="store.scrapes.sort((a,b) => b.scrape_time > a.scrape_time ? 1 : -1)"
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
>>> span { color:white; }
</style>
