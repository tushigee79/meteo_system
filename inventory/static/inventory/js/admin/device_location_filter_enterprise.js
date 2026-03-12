(function () {
  "use strict";

  console.log("DEVICE LOCATION JS ENTERPRISE v2 LOADED");

  function byId(id) {
    return document.getElementById(id);
  }

  function getJQuery() {
    if (window.django && window.django.jQuery) return window.django.jQuery;
    if (window.jQuery) return window.jQuery;
    return null;
  }

  function firstExisting(ids) {
    for (let i = 0; i < ids.length; i++) {
      const el = byId(ids[i]);
      if (el) return el;
    }
    return null;
  }

  function findSelects() {
    return {
      aimag: firstExisting(["id_admin_aimag", "id_aimag_ref", "id_aimag", "id_aimag_id"]),
      sum: firstExisting(["id_admin_sum", "id_sum_ref", "id_sum", "id_sum_id"]),
      location: firstExisting(["id_location", "id_location_id"]),
    };
  }

  function getBaseAdminUrl() {
    return window.location.pathname
      .replace(/add\/$/, "")
      .replace(/[^/]+\/change\/$/, "");
  }

  function getUrls() {
    const base = getBaseAdminUrl();
    return {
      sumsUrl: base + "load-sums/",
      locationsUrl: base + "location-options/",
    };
  }

  function hasOption(select, value) {
    const v = String(value);
    return Array.from(select.options).some(function (o) {
      return String(o.value) === v;
    });
  }

  function refreshWidget(select) {
    const $ = getJQuery();
    if (!$) return;
    try {
      $(select).trigger("change");
      $(select).trigger("change.select2");
    } catch (e) {
      console.warn("refreshWidget warning:", e);
    }
  }

  function setOptions(select, items, placeholder, selectedValue) {
    if (!select) return;

    const keep = selectedValue !== undefined && selectedValue !== null && selectedValue !== ""
      ? String(selectedValue)
      : String(select.value || "");

    const list = Array.isArray(items) ? items : [];

    console.log("setOptions:", {
      target: select.id,
      count: list.length,
      keep: keep
    });

    select.innerHTML = "";

    const first = document.createElement("option");
    first.value = "";
    first.textContent = placeholder || "---------";
    select.appendChild(first);

    list.forEach(function (item) {
      const opt = document.createElement("option");
      opt.value = String(item.id);
      opt.textContent = item.name;
      if (String(item.id) === keep) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    if (keep && hasOption(select, keep)) {
      select.value = keep;
    } else {
      select.value = "";
    }

    refreshWidget(select);

    console.log("setOptions done:", {
      target: select.id,
      optionsLength: select.options.length,
      finalValue: select.value
    });
  }

  async function fetchJson(url) {
    console.log("fetchJson ->", url);

    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    const contentType = (response.headers.get("content-type") || "").toLowerCase();

    if (!response.ok) {
      const txt = await response.text().catch(function () { return ""; });
      throw new Error("HTTP " + response.status + " for " + url + "\n" + txt.slice(0, 200));
    }

    if (!contentType.includes("application/json")) {
      const txt = await response.text().catch(function () { return ""; });
      throw new Error("Not JSON for " + url + "\n" + txt.slice(0, 200));
    }

    const data = await response.json();
    console.log("fetchJson <-", data);
    return data;
  }

  async function loadSums(aimagId, selectedSumId) {
    const selects = findSelects();
    const urls = getUrls();

    if (!selects.sum) return [];
    if (!aimagId) {
      setOptions(selects.sum, [], "---------", "");
      return [];
    }

    const url = urls.sumsUrl + "?aimag_id=" + encodeURIComponent(aimagId);
    const data = await fetchJson(url);
    setOptions(selects.sum, data, "---------", selectedSumId);
    return data;
  }

  async function loadLocations(aimagId, sumId, selectedLocationId) {
    const selects = findSelects();
    const urls = getUrls();

    if (!selects.location) return [];
    if (!aimagId) {
      setOptions(selects.location, [], "---------", "");
      return [];
    }

    const params = ["aimag=" + encodeURIComponent(aimagId)];
    if (sumId) params.push("sum=" + encodeURIComponent(sumId));

    const url = urls.locationsUrl + "?" + params.join("&");
    const data = await fetchJson(url);
    setOptions(selects.location, data, "---------", selectedLocationId);
    return data;
  }

  let lastAimagValue = null;
  let lastSumValue = null;
  let handlingAimag = false;
  let handlingSum = false;

  async function handleAimagChange() {
    if (handlingAimag) return;
    handlingAimag = true;

    try {
      const selects = findSelects();
      const aimagId = selects.aimag ? (selects.aimag.value || "") : "";

      console.log("AIMAG CHANGED:", aimagId);

      await loadSums(aimagId, "");
      await loadLocations(aimagId, "", "");

      lastAimagValue = aimagId;
      lastSumValue = selects.sum ? (selects.sum.value || "") : "";
    } catch (err) {
      console.error("AIMAG CHANGE ERROR:", err);
    } finally {
      handlingAimag = false;
    }
  }

  async function handleSumChange() {
    if (handlingSum) return;
    handlingSum = true;

    try {
      const selects = findSelects();
      const aimagId = selects.aimag ? (selects.aimag.value || "") : "";
      const sumId = selects.sum ? (selects.sum.value || "") : "";

      console.log("SUM CHANGED:", sumId);

      await loadLocations(aimagId, sumId, "");

      lastSumValue = sumId;
    } catch (err) {
      console.error("SUM CHANGE ERROR:", err);
    } finally {
      handlingSum = false;
    }
  }

  async function initialLoad() {
    const selects = findSelects();

    const aimagId = selects.aimag ? (selects.aimag.value || "") : "";
    const sumId = selects.sum ? (selects.sum.value || "") : "";
    const locationId = selects.location ? (selects.location.value || "") : "";

    console.log("INITIAL VALUES:", {
      aimag: aimagId,
      sum: sumId,
      location: locationId
    });

    if (aimagId) {
      await loadSums(aimagId, sumId);
      const effectiveSum = selects.sum ? (selects.sum.value || sumId || "") : "";
      await loadLocations(aimagId, effectiveSum, locationId);
    } else {
      if (selects.sum) setOptions(selects.sum, [], "---------", "");
      if (selects.location) setOptions(selects.location, [], "---------", "");
    }

    lastAimagValue = aimagId;
    lastSumValue = sumId;
  }

  function bindDelegatedEvents() {
    const $ = getJQuery();
    if (!$) return;

    const aimagSelector = "#id_admin_aimag, #id_aimag_ref, #id_aimag, #id_aimag_id";
    const sumSelector = "#id_admin_sum, #id_sum_ref, #id_sum, #id_sum_id";

    $(document).off(".deviceCascade");

    $(document).on("change.deviceCascade select2:select.deviceCascade select2:clear.deviceCascade select2:close.deviceCascade", aimagSelector, function () {
      handleAimagChange();
    });

    $(document).on("change.deviceCascade select2:select.deviceCascade select2:clear.deviceCascade select2:close.deviceCascade", sumSelector, function () {
      handleSumChange();
    });
  }

  function startValueWatcher() {
    setInterval(function () {
      const selects = findSelects();
      const aimagVal = selects.aimag ? (selects.aimag.value || "") : "";
      const sumVal = selects.sum ? (selects.sum.value || "") : "";

      if (aimagVal !== lastAimagValue) {
        handleAimagChange();
        return;
      }

      if (sumVal !== lastSumValue) {
        handleSumChange();
      }
    }, 400);
  }

  async function init() {
    const selects = findSelects();
    const urls = getUrls();

    console.log("init called");
    console.log("Resolved urls:", urls);
    console.log("Selects found:", selects);

    if (!selects.aimag || !selects.sum || !selects.location) {
      console.warn("Required selects missing. Script aborted.", selects);
      return;
    }

    bindDelegatedEvents();
    await initialLoad();
    startValueWatcher();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();