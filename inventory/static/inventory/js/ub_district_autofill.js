/* inventory/static/inventory/js/ub_district_autofill.js
 *
 * Requires Leaflet on the page.
 * Assumes the form has:
 *   - input#id_latitude
 *   - input#id_longitude
 *   - input#id_district_name  (or change selector below)
 *
 * It loads UB districts GeoJSON from /static/data/ub_districts.geojson
 * Then:
 *   - click on map OR drag marker -> fills lat/lon and district via API
 */
(function () {
  if (typeof L === "undefined") return;

  // --- CONFIG ---
  const MAP_ID = "map"; // <div id="map"></div>
  const LAT_SEL = "#id_latitude";
  const LON_SEL = "#id_longitude";
  const DISTRICT_SEL = "#id_district_name"; // change if your field name differs
  const GEOJSON_URL = "/static/data/ub_districts.geojson";
  const LOOKUP_API = "/api/geo/lookup-district/";

  const latEl = document.querySelector(LAT_SEL);
  const lonEl = document.querySelector(LON_SEL);
  const distEl = document.querySelector(DISTRICT_SEL);

  const mapEl = document.getElementById(MAP_ID);
  if (!mapEl) return;

  const map = L.map(MAP_ID).setView([47.918, 106.917], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap"
  }).addTo(map);

  let marker = null;

  function setForm(lat, lon) {
    if (latEl) latEl.value = lat.toFixed(6);
    if (lonEl) lonEl.value = lon.toFixed(6);
  }

  async function lookupDistrict(lat, lon) {
    try {
      const url = `${LOOKUP_API}?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
      const r = await fetch(url, { credentials: "same-origin" });
      const j = await r.json();
      if (j.ok && j.found) {
        if (distEl) distEl.value = j.district || "";
      } else {
        if (distEl) distEl.value = "";
      }
    } catch (e) {
      // silent
    }
  }

  function onPick(lat, lon) {
    setForm(lat, lon);
    lookupDistrict(lat, lon);
    if (!marker) {
      marker = L.marker([lat, lon], { draggable: true }).addTo(map);
      marker.on("dragend", () => {
        const p = marker.getLatLng();
        onPick(p.lat, p.lng);
      });
    } else {
      marker.setLatLng([lat, lon]);
    }
  }

  map.on("click", (e) => onPick(e.latlng.lat, e.latlng.lng));

  fetch(GEOJSON_URL)
    .then(r => r.json())
    .then(gj => {
      L.geoJSON(gj, {
        style: () => ({ weight: 2, fillOpacity: 0.05 }),
        onEachFeature: (feature, layer) => {
          layer.on("click", (e) => {
            const p = e.latlng;
            onPick(p.lat, p.lng);
          });
          const nm = feature?.properties?.name_mn || "District";
          layer.bindTooltip(nm, { sticky: true });
        }
      }).addTo(map);
    });
})();