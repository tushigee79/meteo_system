(function ($) {
  "use strict";

  let lastAimag = null;
  let lastSum = null;
  let lastKind = null;

  function resetSelect($el, placeholder) {
    if (!$el.length) return;
    $el.empty();
    $el.append($("<option>").val("").text(placeholder || "---------"));
    $el.val("");
  }

  function fillSelect($el, rows, placeholder, selectedValue) {
    resetSelect($el, placeholder);
    (rows || []).forEach(function (row) {
      $el.append(
        $("<option>")
          .val(row.id)
          .text(row.name || row.text || ("#" + row.id))
      );
    });

    if (selectedValue) {
      $el.val(String(selectedValue));
    }
    $el.trigger("change");
  }

  function valOf(selector) {
    const $el = $(selector);
    if (!$el.length) return "";
    return ($el.val() || "").toString().trim();
  }

  function loadSums() {
    const aimagId = valOf("#id_aimag");
    const currentSum = valOf("#id_sum");
    const $sum = $("#id_sum");
    const $location = $("#id_location");

    resetSelect($sum, "---------");
    resetSelect($location, "---------");

    if (!aimagId || !window.__deviceSumsUrl) return;

    $.getJSON(window.__deviceSumsUrl, { aimag_id: aimagId })
      .done(function (data) {
        fillSelect($sum, data.sums || data.results || data || [], "---------", currentSum);
      })
      .fail(function (xhr) {
        console.error("loadSums failed:", xhr.status, xhr.responseText);
      });
  }

  function loadLocations() {
    const aimagId = valOf("#id_aimag");
    const sumId = valOf("#id_sum");
    const kind = valOf("#id_kind").toUpperCase();
    const currentLocation = valOf("#id_location");
    const $location = $("#id_location");

    resetSelect($location, "---------");

    if (!sumId || !window.__deviceLocUrl) return;

    $.getJSON(window.__deviceLocUrl, {
      aimag_id: aimagId,
      sum_id: sumId,
      kind: kind
    })
      .done(function (data) {
        fillSelect($location, data.locations || data.results || data || [], "---------", currentLocation);
      })
      .fail(function (xhr) {
        console.error("loadLocations failed:", xhr.status, xhr.responseText);
      });
  }

  $(function () {
    if (!$("#id_aimag").length || !$("#id_sum").length) {
      return;
    }

    lastAimag = valOf("#id_aimag");
    lastSum = valOf("#id_sum");
    lastKind = valOf("#id_kind");

    $("#id_aimag").on("change", function () {
      lastAimag = valOf("#id_aimag");
      loadSums();
    });

    $("#id_sum").on("change", function () {
      lastSum = valOf("#id_sum");
      loadLocations();
    });

    $("#id_kind").on("change", function () {
      const kind = valOf("#id_kind");
      if (kind !== lastKind) {
        lastKind = kind;
        loadLocations();
      }
    });

    if (lastAimag && !$("#id_sum option").length > 1) {
      loadSums();
    }
    if (lastSum) {
      loadLocations();
    }
  });
})(django.jQuery);