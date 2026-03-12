/* static/inventory/js/dashboard_table.js */
(function () {
  function $(id) { return document.getElementById(id); }

  function setState(txt, isError) {
    const el = $("ajax_state");
    if (!el) return;
    el.textContent = txt || "";
    el.style.color = isError ? "crimson" : "";
  }

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function looksLikeHtml(text) {
    const t = (text || "").trim();
    return t.startsWith("<!DOCTYPE") || t.startsWith("<html") || t.startsWith("<");
  }

  function buildBaseUrl() {
    return window.location.origin + window.location.pathname;
  }

  async function fetchJson(url) {
    const res = await fetch(url, {
      headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    const text = await res.text();

    if (looksLikeHtml(text)) {
      const dbg = $("debugBox");
      if (dbg) {
        dbg.style.display = "block";
        dbg.textContent = text.slice(0, 900);
      }
      throw new Error("Server returned HTML instead of JSON (check ?ajax=1 split).");
    }
    return JSON.parse(text);
  }

  async function loadTable() {
    try {
      setState("Хүснэгт уншиж байна...");

      const base = buildBaseUrl();
      const url = new URL(base);

      // ✅ Table JSON endpoint
      url.searchParams.set("ajax", "1");

      // filters
      url.searchParams.set("report", $("id_report")?.value || "maintenance");
      url.searchParams.set("performer", $("id_performer")?.value || "");

      const dateFrom = $("id_date_from")?.value || "";
      const dateTo = $("id_date_to")?.value || "";
      if (dateFrom) url.searchParams.set("date_from", dateFrom);
      if (dateTo) url.searchParams.set("date_to", dateTo);

      const data = await fetchJson(url.toString());

      $("kpi_total").textContent = data.meta?.total ?? 0;
      $("kpi_done").textContent = data.meta?.done ?? 0;
      $("kpi_pending").textContent = data.meta?.pending ?? 0;

      const cols = data.columns || [];
      const rows = data.rows || [];

      const thead = $("table_head");
      thead.innerHTML = cols.map(c =>
        `<th style="text-align:left; padding:12px; border-bottom:2px solid #dee2e6; white-space:nowrap;">${esc(c)}</th>`
      ).join("");

      const tbody = $("tbody");
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="${cols.length || 1}" style="padding:12px; opacity:.7;">Өгөгдөл олдсонгүй</td></tr>`;
        setState("Хоосон");
        return;
      }

      tbody.innerHTML = rows.map(r => {
        const tds = (r || []).map(v => `<td style="padding:10px; border-bottom:1px solid #eee;">${esc(v)}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("");

      setState("Шинэчлэгдсэн");
    } catch (err) {
      console.error("Table Load Error:", err);
      setState("Хүснэгт алдаа (JSON биш)", true);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadTable();
    $("btn_filter")?.addEventListener("click", () => loadTable());
    $("id_performer")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadTable();
    });
  });
})();