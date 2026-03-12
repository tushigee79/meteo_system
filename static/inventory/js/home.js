/* static/inventory/js/home.js */
(function () {
  "use strict";

  function onDashboardHome() {
    const p = window.location.pathname || "";
    // dashboard_home чинь өөр route байвал энд зөвхөн prefix-ээ сольчих
    return p.startsWith("/django-admin/dashboard");
  }

  function pickInt(obj, keys) {
    const lower = {};
    Object.keys(obj || {}).forEach(k => lower[String(k).toLowerCase()] = obj[k]);
    for (const k of keys) {
      const v = lower[String(k).toLowerCase()];
      if (v !== undefined && v !== null) return Number(v) || 0;
    }
    return 0;
  }

  function initStatusChart() {
    if (!onDashboardHome()) return;

    const statusEl =
      document.getElementById("devices-by-status") ||
      document.getElementById("chartStatus");

    // ✅ энэ хуудсанд элемент байхгүй бол чимээгүй алгас
    if (!statusEl) return;

    // ✅ echarts байхгүй бол чимээгүй алгас
    if (!window.echarts) return;

    fetch("/django-admin/inventory/workflow/pending-counts/")
      .then(r => r.json())
      .then(data => {
        // data хэлбэр чинь янз бүр байж болно: аль алинд нь даана
        const labels = ["Done", "Pending", "Need approval", "Rejected"];
        const values = [
          pickInt(data, ["done", "completed", "approved"]),
          pickInt(data, ["pending"]),
          pickInt(data, ["need_approval", "needapproval", "need-approval"]),
          pickInt(data, ["rejected"]),
        ];

        const chart = echarts.init(statusEl);
        chart.setOption({
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: labels },
          yAxis: { type: "value", minInterval: 1 },
          series: [{ type: "bar", data: values }],
        }, true);
      })
      .catch(() => {
        // dashboard дээр ч гэсэн console spam хийхгүй
      });
  }

  document.addEventListener("DOMContentLoaded", initStatusChart);
})();