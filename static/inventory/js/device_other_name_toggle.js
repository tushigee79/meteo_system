(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function findRowForField(fieldId) {
    const el = document.getElementById(fieldId);
    if (!el) return null;
    return el.closest(".form-row") || el.closest(".fieldBox") || el.parentElement;
  }

  function toggleOtherName() {
    const catalog = document.getElementById("id_catalog_item");
    const other = document.getElementById("id_other_name");
    const otherRow = findRowForField("id_other_name");

    if (!catalog || !otherRow) return;

    const selectedText = (catalog.options[catalog.selectedIndex] || {}).text || "";
    const isOther = selectedText.startsWith("Бусад:");

    otherRow.style.display = isOther ? "" : "none";

    if (!isOther && other) {
      other.value = "";
    }
  }

  ready(function () {
    toggleOtherName();
    const catalog = document.getElementById("id_catalog_item");
    if (catalog) catalog.addEventListener("change", toggleOtherName);
  });
})();
