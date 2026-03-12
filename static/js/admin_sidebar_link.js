(function () {

  function forceGo(url) {
    window.location.assign(url);
  }

  function makeBtn(id, text, iconClass, bg, url) {

    const a = document.createElement("a");
    a.id = id;
    a.href = url;
    a.className = "nav-link";
    a.setAttribute("role", "button");

    a.style.cssText =
      "background:" + bg +
      ";color:#fff;margin:6px;border-radius:6px;cursor:pointer;";

    a.innerHTML =
      '<i class="nav-icon ' + iconClass + '"></i>' +
      '<p style="margin:0;">' + text + "</p>";

    a.onclick = function (e) {
      e.preventDefault();
      forceGo(url);
    };

    const li = document.createElement("li");
    li.className = "nav-item";
    li.appendChild(a);

    return li;
  }

  function inject() {

    const menu =
      document.querySelector("ul.nav.nav-pills.nav-sidebar") ||
      document.querySelector(".nav-sidebar");

    if (!menu) return;

    if (!document.getElementById("nav-dashboard-general")) {

      menu.prepend(
        makeBtn(
          "nav-dashboard-general",
          "Dashboard",
          "fas fa-chart-line",
          "#0d6efd",
          "/django-admin/dashboard/general/"
        )
      );

    }

    if (!document.getElementById("nav-reports")) {

      menu.prepend(
        makeBtn(
          "nav-reports",
          "График тайлан",
          "fas fa-chart-pie",
          "#28a745",
          "/django-admin/reports/"
        )
      );

    }

    if (!document.getElementById("nav-admin-entry")) {

      menu.prepend(
        makeBtn(
          "nav-admin-entry",
          "Өгөгдөл бүртгэх",
          "fas fa-edit",
          "#6f42c1",
          "/django-admin/"
        )
      );

    }

  }

  document.addEventListener("DOMContentLoaded", inject);

})();