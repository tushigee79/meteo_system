document.addEventListener("DOMContentLoaded", function () {

  // =========================
  // Devices by Status
  // =========================
  const statusEl = document.getElementById("devices-by-status");
  if (statusEl && typeof echarts !== "undefined") {
    fetch("/inventory/workflow/pending-counts/")
      .then(r => r.json())
      .then(data => {
        const labels = Object.keys(data);
        const values = labels.map(k => data[k]);

        const chart = echarts.init(statusEl);
        chart.setOption({
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: labels },
          yAxis: { type: "value", minInterval: 1 },
          series: [{ type: "bar", data: values }]
        });
      });
  }

  // =========================
  // Broken by Aimag
  // =========================
  const aimagEl = document.getElementById("aimagChart");
  if (aimagEl && typeof echarts !== "undefined") {
    fetch("/inventory/workflow/broken-by-aimag/?limit=10")
      .then(r => r.json())
      .then(rows => {
        const labels = rows.map(r => r.name);
        const values = rows.map(r => r.count);

        const chart = echarts.init(aimagEl);
        chart.setOption({
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: labels },
          yAxis: { type: "value", minInterval: 1 },
          series: [{
            type: "bar",
            data: values,
            itemStyle: { color: "#dc3545" }
          }]
        });
      });
  }

});
