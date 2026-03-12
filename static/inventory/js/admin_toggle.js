(function () {
  function byName(name) {
    return document.querySelector(`[name="${name}"]`);
  }
  function rowForInput(el) {
    if (!el) return null;
    return el.closest(".form-row") || el.closest(".fieldBox") || el.parentElement;
  }

  function toggleDeviceOther() {
    const dcub = byName("dcub_type");
    const other = byName("other_name");
    const otherRow = rowForInput(other);
    if (!dcub || !otherRow) return;

    if (dcub.value === "OTHER") {
      otherRow.style.display = "";
    } else {
      otherRow.style.display = "none";
      if (other) other.value = "";
    }
  }

  function toggleMaintenance() {
    const type = byName("performed_by_type");
    const eng = byName("engineer_name");
    const org = byName("organization_name");

    const engRow = rowForInput(eng);
    const orgRow = rowForInput(org);

    if (!type) return;

    if (type.value === "ENGINEER") {
      if (engRow) engRow.style.display = "";
      if (orgRow) orgRow.style.display = "none";
      if (org) org.value = "";
    } else {
      if (engRow) engRow.style.display = "none";
      if (orgRow) orgRow.style.display = "";
      if (eng) eng.value = "";
    }
  }

  function toggleCalibration() {
    const choice = byName("lab_choice");
    const org = byName("lab_org");
    const other = byName("lab_other_name");

    const orgRow = rowForInput(org);
    const otherRow = rowForInput(other);

    if (!choice) return;

    if (choice.value === "BOHZT") {
      if (orgRow) orgRow.style.display = "";
      if (otherRow) otherRow.style.display = "none";
      if (other) other.value = "";
    } else {
      if (orgRow) orgRow.style.display = "none";
      if (otherRow) otherRow.style.display = "";
      if (org) org.value = "";
    }
  }

  document.addEventListener("change", function (e) {
    if (e.target && e.target.name === "dcub_type") toggleDeviceOther();
    if (e.target && e.target.name === "performed_by_type") toggleMaintenance();
    if (e.target && e.target.name === "lab_choice") toggleCalibration();
  });

  document.addEventListener("DOMContentLoaded", function () {
    toggleDeviceOther();
    toggleMaintenance();
    toggleCalibration();
  });
})();
