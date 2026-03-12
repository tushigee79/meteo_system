function addSafeTileLayer(map){
  const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, crossOrigin: true,
    attribution: "&copy; OpenStreetMap contributors",
  });
  const carto = L.tileLayer("https://cartodb-basemaps.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap & CartoDB",
  });
  osm.addTo(map);
  osm.on("tileerror", function(){
    console.warn("OSM tile error/blocked. Switching to Carto...");
    try{ map.removeLayer(osm); }catch(e){}
    carto.addTo(map);
  });
}
