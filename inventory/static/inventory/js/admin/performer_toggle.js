// inventory/static/inventory/js/admin/performer_toggle.js
(function () {
  function rowForField(fieldName) {
    // Django admin default: .form-row.field-<name>
    return document.querySelector(".form-row.field-" + fieldName);
  }

  function setVisible(el, visible) {
    if (!el) return;
    el.style.display = visible ? "" : "none";
  }

  function apply() {
    const typeEl = document.getElementById("id_performer_type");
    if (!typeEl) return;

    const engineerRow = rowForField("performer_engineer_name");
    const orgRow = rowForField("performer_org_name");

    const v = typeEl.value;
    if (v === "ENGINEER") {
      setVisible(engineerRow, true);
      setVisible(orgRow, false);
    } else if (v === "ORG") {
      setVisible(engineerRow, false);
      setVisible(orgRow, true);
    } else {
      // fallback
      setVisible(engineerRow, true);
      setVisible(orgRow, true);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const typeEl = document.getElementById("id_performer_type");
    if (typeEl) {
      typeEl.addEventListener("change", apply);
      apply();
    }
  });
})();
