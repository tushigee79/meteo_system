(function () {
  // Auto-submit changelist filter forms when a select changes.
  // Works for:
  // - Device changelist: #dev-filter-form with #filter_kind
  // - InstrumentCatalog changelist: #cat-filter-form with #filter_kind
  // - Location changelist: handled by location_changelist_cascade.js (kept)
  function bind(formId, selectIds) {
    var form = document.getElementById(formId);
    if (!form) return;
    (selectIds || []).forEach(function (sid) {
      var el = document.getElementById(sid);
      if (!el) return;
      el.addEventListener("change", function () {
        form.submit();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bind("dev-filter-form", ["filter_kind", "filter_status"]);
    bind("cat-filter-form", ["filter_kind", "filter_active"]);
  });
})();