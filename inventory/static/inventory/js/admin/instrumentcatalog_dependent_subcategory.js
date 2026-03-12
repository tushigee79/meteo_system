(function () {
  function byId(id) { return document.getElementById(id); }

  async function fetchOptions(category) {
    const url = window.__instrumentcatalog_subcat_url;
    if (!url) return [];
    const u = new URL(url, window.location.origin);
    u.searchParams.set("category", category || "");
    const r = await fetch(u.toString(), { credentials: "same-origin" });
    if (!r.ok) return [];
    const data = await r.json();
    return data.options || [];
  }

  function setOptions(selectEl, options) {
    const current = selectEl.value;
    selectEl.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "---------";
    selectEl.appendChild(empty);

    options.forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      selectEl.appendChild(o);
    });

    // өмнөх утга боломжтой бол хадгална
    if (options.includes(current)) selectEl.value = current;
  }

  async function onChange() {
    const cat = byId("id_category");
    const sub = byId("id_subcategory");
    if (!cat || !sub) return;
    const opts = await fetchOptions(cat.value);
    setOptions(sub, opts);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const cat = byId("id_category");
    const sub = byId("id_subcategory");
    if (!cat || !sub) return;
    cat.addEventListener("change", onChange);
    onChange();
  });
})();
