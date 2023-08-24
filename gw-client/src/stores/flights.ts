import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { API } from '@/api'
import type { Scrape } from '@/api'

export const useFlightStore = defineStore('flights', () => {
  
  const scrapes = ref([] as Scrape[]);
  const selectedScrape = ref(null as Scrape | null);
  const origin = ref('') as any;
  
  const loadScrapes = async () => {
    scrapes.value = await API.getScrapes()
  }
      
  const loadScrape = async (id: number) => {
    selectedScrape.value = await API.getScrape(id)
    origin.value = selectedScrape.value.destinations[0].from_iata
  }

  return { scrapes, selectedScrape, origin, loadScrapes, loadScrape }
  
})
