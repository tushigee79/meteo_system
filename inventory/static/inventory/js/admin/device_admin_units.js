(function () {
  const aimag = document.getElementById("id_admin_aimag");
  const sum = document.getElementById("id_admin_sum");
  const loc = document.getElementById("id_location");

  if (!aimag || !sum || !loc) return;

  function clear(sel) {
    sel.innerHTML = '<option value="">---------</option>';
  }

  async function fetchJson(url) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) return null;
    return await r.json();
  }

  async function loadSums() {
    clear(sum); clear(loc);
    if (!aimag.value) return;

    const data = await fetch(`/ajax/load-sums/?aimag_id=${aimag.value}`).then(r => r.json());
    (data.sums || []).forEach(s => {
      sum.add(new Option(s.name, s.id));
    });
  }

  async function loadLocations() {
    clear(loc);
    if (!sum.value) return;

    const data = await fetch(`/ajax/location-by-sum/?sum_id=${sum.value}`).then(r => r.json());
    (data.results || []).forEach(l => {
      loc.add(new Option(l.text, l.id));
    });
  }

  aimag.addEventListener("change", loadSums);
  sum.addEventListener("change", loadLocations);

  if (aimag.value) loadSums();
})();