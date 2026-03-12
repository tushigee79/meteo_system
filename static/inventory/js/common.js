(function (factory) {
  const $ = (window.django && window.django.jQuery) ? window.django.jQuery : window.jQuery;
  if (!$) {
    console.warn("common.js: jQuery not available on this page. Skipping.");
    return;
  }
  factory($);
})(function ($) {
  "use strict";

  // Keep Jazzmin sidebar state (open/closed) in cookie
  function setCookie(key, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${key}=${encodeURIComponent(value)};expires=${d.toUTCString()};SameSite=Strict;path=/`;
  }

  function getCookie(key) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + key.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }

  function handleMenu() {
    // Jazzmin uses pushmenu toggler
    $('[data-widget="pushmenu"]').on("click", function () {
      const closed = getCookie("jazzy_menu") === "closed";
      setCookie("jazzy_menu", closed ? "open" : "closed", 30);
    });
  }

  function setActiveLinks() {
    const currentUrl = window.location.href.split("#")[0].split("?")[0];

    $("ul.nav-sidebar a").each(function () {
      // normalize trailing slash
      const href = (this.href || "").split("#")[0].split("?")[0];
      if (href === currentUrl) {
        $(this).addClass("active");

        const parent = $(this).parents("li.nav-item").first();
        parent.addClass("menu-open");
        parent.children("a").addClass("active");
      }
    });
  }

  $(function () {
    setActiveLinks();
    handleMenu();
  });
});