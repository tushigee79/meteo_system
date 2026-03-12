(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  async function fetchSums(aimagId) {
    const url = new URL(window.location.origin + "/django-admin/inventory/location/sums-by-aimag/");
    url.searchParams.set("aimag_id", aimagId || "");
    const res = await fetch(url.toString(), { credentials: "same-origin" });
    return await res.json();
  }

  function rebuild(selectEl, items) {
    while (selectEl.options.length) selectEl.remove(0);
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.text = "---------";
    selectEl.add(opt0);

    (items || []).forEach((it) => {
      const opt = document.createElement("option");
      opt.value = it.id;
      opt.text = it.text;
      selectEl.add(opt);
    });
  }

  ready(function () {
    const aimagEl = document.getElementById("id_aimag_ref");
    const sumEl = document.getElementById("id_sum_ref");
    if (!aimagEl || !sumEl) return;

    async function refresh() {
      const data = await fetchSums(aimagEl.value);
      rebuild(sumEl, data.results || []);
    }

    aimagEl.addEventListener("change", () => refresh().catch(console.error));
    refresh().catch(console.error);
  });
})();
