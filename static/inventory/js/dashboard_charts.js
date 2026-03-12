/* static/inventory/js/dashboard_charts.js */
(function () {

  function fetchJson(url) {
    return fetch(url, {
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
      },
      credentials: "same-origin"
    }).then(async (r) => {

      const text = await r.text();
      const t = (text || "").trim();

      if (t.startsWith("<!DOCTYPE") || t.startsWith("<html") || t.startsWith("<")) {
        throw new Error("Charts endpoint returned HTML (check URL mapping / permissions).");
      }

      return JSON.parse(text);
    });
  }

  function chartsEndpoint() {
    return window.location.origin + "/django-admin/api/reports/charts/";
  }

  let sChart = null;
  let wChart = null;

  async function loadCharts() {

    try {

      if (typeof echarts === "undefined") {
        console.error("echarts is not loaded (missing echarts.min.js)");
        return;
      }

      const url = new URL(chartsEndpoint());
      url.searchParams.set("ajax", "1");

      const data = await fetchJson(url.toString());

      // ---------- status chart ----------
      const sEl = document.getElementById("status_chart");

      if (sEl) {

        if (!sChart) sChart = echarts.init(sEl);

        const axis = data.devices_by_status?.axis || [];
        const seriesObj = data.devices_by_status?.series || {};
        const keys = Object.keys(seriesObj);

        if (!axis.length || !keys.length) {

          sChart.clear();

          sChart.setOption({
            title: { text: "Төхөөрөмжийн төлөв" },
            graphic: [{
              type: "text",
              left: "center",
              top: "middle",
              style: {
                text: "Өгөгдөл алга",
                fontSize: 14,
                opacity: 0.6
              }
            }]
          });

        } else {

          sChart.setOption({
            title: { text: "Төхөөрөмжийн төлөв", textStyle: { fontSize: 14 } },
            tooltip: { trigger: "axis" },
            legend: { top: 30 },
            grid: { left: 40, right: 20, top: 80, bottom: 40 },
            xAxis: { type: "category", data: axis },
            yAxis: { type: "value" },
            series: keys.map(k => ({
              name: k,
              type: "line",
              smooth: true,
              data: seriesObj[k] || []
            })),
          }, true);

        }
      }

      // ---------- workflow chart ----------
      const wEl = document.getElementById("workflow_chart");

      if (wEl) {

        if (!wChart) wChart = echarts.init(wEl);

        const axis = data.workflow?.axis || [];
        const ms = data.workflow?.ms || [];
        const ca = data.workflow?.ca || [];

        if (!axis.length) {

          wChart.clear();

          wChart.setOption({
            title: { text: "Засвар & Тохируулга" },
            graphic: [{
              type: "text",
              left: "center",
              top: "middle",
              style: {
                text: "Өгөгдөл алга",
                fontSize: 14,
                opacity: 0.6
              }
            }]
          });

        } else {

          wChart.setOption({
            title: { text: "Засвар & Тохируулга", textStyle: { fontSize: 14 } },
            tooltip: { trigger: "axis" },
            legend: { top: 30 },
            grid: { left: 40, right: 20, top: 80, bottom: 40 },
            xAxis: { type: "category", data: axis },
            yAxis: { type: "value" },
            series: [
              { name: "Засвар", type: "bar", data: ms },
              { name: "Тохируулга", type: "bar", data: ca }
            ],
          }, true);

        }
      }

    } catch (e) {

      console.error("Charts Load Error:", e);

    }
  }

  document.addEventListener("DOMContentLoaded", () => {

    loadCharts();

    window.addEventListener("resize", () => {
      try { sChart?.resize(); } catch (e) {}
      try { wChart?.resize(); } catch (e) {}
    });

  });

})();