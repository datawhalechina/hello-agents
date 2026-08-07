<template>
  <div ref="mapEl" class="map-container"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'

defineOptions({ name: 'SiteMap' })

const props = defineProps({
  sites: {
    type: Array,
    default: () => []
  },
  selectedSiteId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select'])
const mapEl = ref(null)
let map = null
let markers = []
let labels = []

function markerColor(siteId) {
  return siteId === props.selectedSiteId ? '#c7382f' : '#1864ab'
}

function drawMarkers() {
  markers.forEach((m) => m.remove())
  labels.forEach((l) => l.remove())
  markers = []
  labels = []

  props.sites.forEach((site) => {
    const isSelected = site.site_id === props.selectedSiteId
    const marker = L.circleMarker([site.latitude, site.longitude], {
      radius: isSelected ? 11 : 8,
      color: markerColor(site.site_id),
      weight: 2,
      fillOpacity: 0.8
    })
    marker.bindPopup(
      `<b>${site.site_name}</b><br/>${site.province}${site.city}<br/>` +
      `经纬度: ${site.latitude.toFixed(2)}, ${site.longitude.toFixed(2)}`
    )
    marker.on('click', () => emit('select', site))
    marker.addTo(map)
    markers.push(marker)

    const label = L.marker([site.latitude + 0.18, site.longitude + 0.22], {
      interactive: false,
      icon: L.divIcon({
        className: 'site-label',
        html: `<span>${site.city}</span>`
      })
    })
    label.addTo(map)
    labels.push(label)

    if (isSelected) {
      marker.openPopup()
      map.flyTo([site.latitude, site.longitude], Math.max(map.getZoom(), 6), { duration: 0.6 })
    }
  })

  if (props.sites.length > 1 && !props.selectedSiteId) {
    const bounds = L.latLngBounds(props.sites.map((s) => [s.latitude, s.longitude]))
    map.fitBounds(bounds.pad(0.45))
  }
}

onMounted(() => {
  map = L.map(mapEl.value).setView([35.5, 104.5], 4.2)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
  }).addTo(map)
  L.control.scale({ imperial: false }).addTo(map)
  drawMarkers()
})

watch(() => props.sites, drawMarkers, { deep: true })
watch(() => props.selectedSiteId, drawMarkers)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>
