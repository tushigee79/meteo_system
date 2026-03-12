(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  async function fetchCatalog(kind) {
    const url = new URL(window.location.origin + "/django-admin/inventory/device/catalog-by-kind/");
    url.searchParams.set("kind", kind || "");
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
    const kindEl = document.getElementById("id_kind");
    const catEl = document.getElementById("id_catalog_item");
    if (!kindEl || !catEl) return;

    async function refresh() {
      const data = await fetchCatalog(kindEl.value);
      rebuild(catEl, data.results || []);
    }

    kindEl.addEventListener("change", () => refresh().catch(console.error));
    refresh().catch(console.error);
  });
})();
