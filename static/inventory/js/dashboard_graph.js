(function () {
  // ---------- helpers ----------
  function $(id) { return document.getElementById(id); }

  const TYPE_COLORS = {
    AWS: "#1f77b4",
    RADAR: "#d62728",
    AEROLOGY: "#2ca02c",
    HYDRO: "#17becf",
    METEO: "#9467bd",
    AGRO: "#8c564b",
    ETALON: "#ff7f0e",
    OTHER: "#7f7f7f",
  };

  function setState(text, isError) {
    const el = $("ajaxState");
    if (!el) return;
    el.textContent = text;
    el.style.background = isError ? "rgba(231,74,59,.12)" : "rgba(0,0,0,.05)";
    el.style.color = isError ? "#a11" : "#333";
  }

  function buildUrl() {
    const params = new URLSearchParams();
    params.set("ajax", "1");

    const dateFrom = $("date_from")?.value?.trim();
    const dateTo = $("date_to")?.value?.trim();
    const aimagId = $("aimag_id")?.value?.trim();
    const kind = $("kind")?.value?.trim(); // input дээр "AWS, RADAR..."

    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (aimagId) params.set("aimag_id", aimagId);
    if (kind) params.set("location_types", kind);

    const base = (window.DASH_GRAPH_DATA_URL || window.location.pathname).trim();
    return base + "?" + params.toString();
  }

  function safeArray(x) { return Array.isArray(x) ? x : []; }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // ---------- charts ----------
  let chartWorkflow, chartSla, chartAimag, chartKind;

  function initCharts() {
    if (!window.echarts) {
      setState("ECharts not loaded", true);
      return;
    }

    const elW = $("chart_workflow");
    const elS = $("chart_sla");
    const elA = $("chart_aimag");
    const elK = $("chart_kind");
    if (!elW || !elS || !elA || !elK) {
      setState("Chart containers missing", true);
      return;
    }

    chartWorkflow = echarts.init(elW);
    chartSla = echarts.init(elS);
    chartAimag = echarts.init(elA);
    chartKind = echarts.init(elK);

    // empty defaults
    chartWorkflow.setOption({ series: [{ type: "pie", data: [] }] });
    chartSla.setOption({ series: [{ type: "pie", data: [] }] });
    chartAimag.setOption({ xAxis: { type: "category", data: [] }, yAxis: { type: "value" }, series: [{ type: "bar", data: [] }] });
    chartKind.setOption({ xAxis: { type: "category", data: [] }, yAxis: { type: "value" }, series: [{ type: "bar", data: [] }] });

    window.addEventListener("resize", () => {
      chartWorkflow?.resize();
      chartSla?.resize();
      chartAimag?.resize();
      chartKind?.resize();
      map?.invalidateSize?.();
    });
  }

  function updateCharts(payload) {
    const wf = safeArray(payload.echarts_workflow_stacked).map(x => ({ name: x.name, value: x.value }));
    const sla = safeArray(payload.echarts_sla).map(x => ({ name: x.name, value: x.value }));
    const aim = safeArray(payload.echarts_aimag);
    const kin = safeArray(payload.echarts_kind);

    chartWorkflow?.setOption({
      tooltip: { trigger: "item" },
      series: [{ type: "pie", radius: "70%", data: wf }],
    });

    chartSla?.setOption({
      tooltip: { trigger: "item" },
      series: [{ type: "pie", radius: "70%", data: sla }],
    });

    chartAimag?.setOption({
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: aim.map(x => x.name) },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: aim.map(x => x.value) }],
    });

    chartKind?.setOption({
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: kin.map(x => x.name) },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: kin.map(x => x.value) }],
    });
  }

  // ---------- map ----------
  let map, markersLayer;

  function initMap() {
    const el = $("map");
    if (!el || !window.L) {
      setState("Leaflet not loaded", true);
      return;
    }

    map = L.map("map").setView([47.9, 106.9], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);
  }

  function updateMap(payload) {
    if (!map || !markersLayer) return;
    markersLayer.clearLayers();

    const pts = safeArray(payload.locations);
    for (const p of pts) {
      if (p.lat == null || p.lon == null) continue;

      const t = String(p.location_type || "").toUpperCase();
      const col = TYPE_COLORS[t] || "#3388ff";

      const marker = L.circleMarker([p.lat, p.lon], {
        radius: 5,
        weight: 1,
        color: col,
        fillColor: col,
        fillOpacity: 0.7,
      });

      marker.bindPopup(`<b>${escapeHtml(p.name || "")}</b><br/>${escapeHtml(p.location_type || "")}`);
      marker.addTo(markersLayer);
    }

    if (pts.length > 0) {
      const bounds = L.latLngBounds(pts.map(p => [p.lat, p.lon]));
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }

  // ---------- fetch + apply ----------
  async function loadAndRender() {
    const url = buildUrl();
    setState("Loading…");

    try {
      const res = await fetch(url, {
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
      });

      const ct = (res.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) {
        const text = await res.text();
        setState("JSON биш хариу ирлээ (HTML буцсан байж магадгүй)", true);
        console.error("NOT JSON:", res.status, ct, text.slice(0, 300));
        return;
      }

      const data = await res.json();
      updateCharts(data);
      updateMap(data);
      setState("Updated");
    } catch (e) {
      setState("Error: " + (e?.message || e), true);
      console.error(e);
    }
  }

  // ---------- init ----------
  document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initMap();

    $("applyBtn")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      loadAndRender();
    });

    // first load
    loadAndRender();
  });
})();