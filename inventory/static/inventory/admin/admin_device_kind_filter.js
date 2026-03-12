(function () {
  function byId(id) { return document.getElementById(id); }
  function qs(sel) { return document.querySelector(sel); }

  function setOptions(selectEl, items, placeholder) {
    if (!selectEl) return;

    const current = selectEl.value;
    selectEl.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder || "---------";
    selectEl.appendChild(opt0);

    (items || []).forEach((it) => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.name;
      selectEl.appendChild(opt);
    });

    // Өмнөх сонголт боломжтой бол хадгална
    if (current) {
      const exists = Array.from(selectEl.options).some(o => o.value === current);
      if (exists) selectEl.value = current;
    }
  }

  async function fetchCatalog(kind) {
    const url = `/inventory/api/catalog/?kind=${encodeURIComponent(kind)}`;
    const res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) return { ok: false, items: [] };
    return await res.json();
  }

  function toggleOtherUI(kind) {
    const catalogSel = byId("id_catalog_item");
    const otherName = byId("id_other_name");

    // other_name мөрийг show/hide
    const otherRow =
      qs(".form-row.field-other_name") ||
      (otherName ? otherName.closest(".form-row") : null);

    const isOther = (kind === "OTHER");

    if (catalogSel) catalogSel.disabled = isOther;

    if (otherRow) otherRow.style.display = isOther ? "" : "none";

    if (otherName) {
      otherName.disabled = !isOther;
      if (isOther) otherName.setAttribute("required", "required");
      else otherName.removeAttribute("required");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const kindSel = byId("id_kind");
    const catalogSel = byId("id_catalog_item");

    if (!kindSel) return;

    async function refreshCatalog() {
      const kind = (kindSel.value || "").trim();

      toggleOtherUI(kind);

      // OTHER эсвэл хоосон үед catalog-ийг зүгээр placeholder болгоод үлдээнэ
      if (!catalogSel) return;

      if (!kind || kind === "OTHER") {
        // сонголтыг цэвэрлэх (хүсвэл comment болгож болно)
        setOptions(catalogSel, [], "---------");
        return;
      }

      try {
        const data = await fetchCatalog(kind);
        if (!data || data.ok === false) return;
        setOptions(catalogSel, data.items || [], "---------");
      } catch (e) {
        // network алдаа гарсан ч admin эвдэхгүй
      }
    }

    kindSel.addEventListener("change", function () {
      // kind солигдоход catalog сонголтыг түр цэвэрлэнэ
      if (catalogSel) catalogSel.value = "";
      refreshCatalog();
    });

    // init
    refreshCatalog();
  });
})();
