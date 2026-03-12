(function ($) {
  "use strict";

  let lastAimag = null;
  let lastSum = null;
  let lastKind = null;

  function resetSelect($el, placeholder) {
    $el.empty();
    $el.append($("<option>").val("").text(placeholder || "---------"));
    $el.val("");
  }

  function fillSelect($el, rows, placeholder) {
    resetSelect($el, placeholder);
    (rows || []).forEach(function (row) {
      $el.append(
        $("<option>")
          .val(row.id)
          .text(row.name || row.text || ("#" + row.id))
      );
    });
    $el.trigger("change");
  }

  function valOf(id) {
    return ($(id).val() || "").toString().trim();
  }

  function loadSums() {
    const aimagId = valOf("#id_admin_aimag");
    const $sum = $("#id_admin_sum");
    const $location = $("#id_location");

    console.log("loadSums(), aimagId =", aimagId);

    resetSelect($sum, "---------");
    resetSelect($location, "---------");
    $sum.trigger("change");
    $location.trigger("change");

    if (!aimagId) return;

    $.getJSON(window.__deviceSumsUrl, { aimag_id: aimagId })
      .done(function (data) {
        console.log("SUMS RESPONSE:", data);
        fillSelect($sum, data.sums || data.results || [], "---------");
      })
      .fail(function (xhr) {
        console.error("loadSums failed:", xhr.status, xhr.responseText);
      });
  }

  function loadLocations() {
    const aimagId = valOf("#id_admin_aimag");
    const sumId = valOf("#id_admin_sum");
    const kind = valOf("#id_kind").toUpperCase();
    const $location = $("#id_location");

    console.log("loadLocations()", { aimagId, sumId, kind });

    resetSelect($location, "---------");
    $location.trigger("change");

    if (!sumId) return;

    $.getJSON(window.__deviceLocUrl, {
      aimag_id: aimagId,
      sum_id: sumId,
      kind: kind
    })
      .done(function (data) {
        console.log("LOCATIONS RESPONSE:", data);
        fillSelect($location, data.locations || data.results || [], "---------");
      })
      .fail(function (xhr) {
        console.error("loadLocations failed:", xhr.status, xhr.responseText);
      });
  }

  $(function () {
    console.log("device_location_cascade.js loaded (polling mode)");

    setInterval(function () {
      const aimag = valOf("#id_admin_aimag");
      const sum = valOf("#id_admin_sum");
      const kind = valOf("#id_kind");

      if (aimag !== lastAimag) {
        console.log("Aimag changed via polling:", lastAimag, "=>", aimag);
        lastAimag = aimag;
        lastSum = sum;
        lastKind = kind;
        loadSums();
        return;
      }

      if (sum !== lastSum) {
        console.log("Sum changed via polling:", lastSum, "=>", sum);
        lastSum = sum;
        loadLocations();
        return;
      }

      if (kind !== lastKind) {
        console.log("Kind changed via polling:", lastKind, "=>", kind);
        lastKind = kind;
        loadLocations();
      }
    }, 400);
  });
})(django.jQuery);