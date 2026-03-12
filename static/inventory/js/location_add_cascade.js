/**
 * Safe cascade script for Location add/change forms.
 * In changelist pages there is no aimag/sum fields -> do nothing.
 */
(function () {
  function $(id) { return document.getElementById(id); }

  // Common field ids in this project (admin forms)
  const aimag = $("id_aimag_ref") || $("id_aimag");
  const sum = $("id_sum_ref") || $("id_sum_duureg_ref") || $("id_sum_duureg") || $("id_sum");

  // If we're not on an add/change form, bail out silently.
  if (!aimag || !sum) {
    console.warn("location_add_cascade: aimag_ref/sum_ref not found");
    return;
  }

  // Existing logic (if any) should live elsewhere; this file only prevents hard errors.
})();
