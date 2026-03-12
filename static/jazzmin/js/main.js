(function($) {
    'use strict';

    function setCookie(key, value) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (value * 24 * 60 * 60 * 1000));
        document.cookie = key + '=' + value + ';expires=' + expires.toUTCString() + '; SameSite=Strict;path=/';
    }

    function getCookie(key) {
        const keyValue = document.cookie.match('(^|;) ?' + key + '=([^;]*)(;|$)');
        return keyValue ? keyValue[2] : null;
    }

    function handleMenu() {
        $('[data-widget=pushmenu]').bind('click', function () {
            const menuClosed = getCookie('jazzy_menu') === 'closed';
            if (!menuClosed) {
                setCookie('jazzy_menu', 'closed');
            } else {
                setCookie('jazzy_menu', 'open');
            }
        });
    }


    function setActiveLinks() {
        /*
         Set the currently active menu item based on the current url, or failing that, find the parent
         item from the breadcrumbs
         */
        const url = window.location.pathname;
        const $breadcrumb = $('.breadcrumb a').last();
        const $link = $('a[href="' + url + '"]');
        const $parent_link = $('a[href="' + $breadcrumb.attr('href') + '"]');

        if ($link.length) {
            $link.addClass('active');
        } else if ($parent_link.length) {
            $parent_link.addClass('active');
        };

        const $a_active = $('a.nav-link.active');
        const $main_li_parent = $a_active.closest('li.nav-item.has-treeview');
        const $ul_child = $main_li_parent.children('ul');

        $ul_child.show();
        $main_li_parent.addClass('menu-is-opening menu-open');
    };

    $(document).ready(function () {
        // Set active status on links
        setActiveLinks()

        // When we use the menu, store its state in a cookie to preserve it
        handleMenu();

        // Add minimal changelist styling to templates that we have been unable to override (e.g MPTT)
        // Needs to be here and not in change_list.js because this is the only JS we are guaranteed to run
        // (as its included in base.html)
        const $changeListTable = $('#changelist .results table');
        if ($changeListTable.length && !$changeListTable.hasClass('table table-striped')) {
            $changeListTable.addClass('table table-striped');
        };
    });
document.addEventListener("DOMContentLoaded", function () {

  function pick(obj, keys) {
    // obj дотор keys-ийн аль нэг нь байвал (том/жижиг үсэг хамаагүй) олж өгнө
    if (!obj) return 0;
    const lower = {};
    Object.keys(obj).forEach(k => lower[String(k).toLowerCase()] = obj[k]);

    for (const k of keys) {
      const v = lower[String(k).toLowerCase()];
      if (v !== undefined && v !== null) return Number(v) || 0;
    }
    return 0;
  }

  // =========================
  // Devices by Status
  // =========================
  const statusEl =
    document.getElementById("devices-by-status") ||
    document.getElementById("chartStatus");

if (!statusEl) {
  console.warn("Status chart element not found. Skipping.");
  return;
}

if (!window.echarts) {
  console.warn("ECharts not loaded.");
  return;
}


  if (statusEl && window.echarts) {

    fetch("/django-admin/inventory/workflow/pending-counts/")
      .then(r => r.json())
      .then(data => {
        console.log("pending-counts raw:", data);

        // ✅ Dashboard дээр чинь PENDING/BROKEN/EMPTY/OK гэж харагдаж байгаа тул
        // backend-ийн key ямар ч байсан энд map хийгээд зөв онооно.
        const labels = ["PENDING", "BROKEN", "EMPTY", "OK"];

        const values = [
          pick(data, ["PENDING", "pending", "pending_count", "in_progress"]),
          pick(data, ["BROKEN", "broken", "fail", "fault", "down"]),
          pick(data, ["EMPTY", "empty", "unknown", "none", "missing"]),
          pick(data, ["OK", "ok", "working", "ready", "active"]),
        ];

        console.log("mapped values:", values);

        const chart = echarts.init(statusEl);
        chart.setOption({
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: labels },
          yAxis: { type: "value", minInterval: 1 },
          series: [{
            type: "bar",
            data: values,
          }],
        }, true); // ✅ notMerge=true
      })
      .catch(err => console.error("pending-counts failed:", err));
  } else {
    console.warn("devices-by-status element not found OR echarts not loaded");
  }

});

})(jQuery);
