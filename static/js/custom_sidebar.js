(function () {
  function injectLink() {
    var menu = document.querySelector("ul.nav.nav-pills.nav-sidebar");
    if (!menu) return false;

    var existing = document.getElementById("nav-admin-section-link");
    if (existing) return true;

    var li = document.createElement("li");
    li.className = "nav-item";

    var a = document.createElement("a");
    a.className = "nav-link";
    a.href = "/django-admin/";
    a.id = "nav-admin-section-link";

    // ✅ clickable болгох “hardening”
    a.setAttribute("target", "_blank");                 // шинэ tab
    a.setAttribute("rel", "noopener noreferrer");
    a.style.cursor = "pointer";
    a.style.pointerEvents = "auto";

    var icon = document.createElement("i");
    icon.className = "nav-icon fas fa-user-shield";

    var p = document.createElement("p");
    p.appendChild(document.createTextNode("Админ хэсэг"));

    a.appendChild(icon);
    a.appendChild(p);
    li.appendChild(a);

    // Dashboard-ын доор байрлуулна
    menu.insertBefore(li, menu.children[1] || menu.firstChild);

    return true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (injectLink()) return;

    var tries = 0;
    var t = setInterval(function () {
      tries += 1;
      if (injectLink() || tries >= 10) clearInterval(t);
    }, 200);
  });
})();
