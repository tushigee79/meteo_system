(function () {
  function qs(sel) { return document.querySelector(sel); }

  function rebuildSelect(selectEl, items) {
    const current = selectEl.value;
    selectEl.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "---------";
    selectEl.appendChild(empty);

    items.forEach((it) => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.text;
      selectEl.appendChild(opt);
    });

    // keep if exists
    if (current) selectEl.value = current;
  }

  async function fetchCatalog(kind) {
    const url = "../catalog-by-kind/?kind=" + encodeURIComponent(kind || "");
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  }

  async function onKindChange() {
    const kindSel = qs("#id_kind");
    const catSel = qs("#id_catalog_item");
    if (!kindSel || !catSel) return;

    const kind = kindSel.value;
    // If no kind, clear
    if (!kind) {
      rebuildSelect(catSel, []);
      return;
    }
    const items = await fetchCatalog(kind);
    rebuildSelect(catSel, items);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const kindSel = qs("#id_kind");
    if (kindSel) {
      kindSel.addEventListener("change", onKindChange);
      // initial (edit page already has kind)
      onKindChange();
    }
  });
})();