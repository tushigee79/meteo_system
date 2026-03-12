(function () {
  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  onReady(function () {
    // Device дээр "Төрөл" байхгүй тул catalog_item.kind-ээр шүүх шийдэлтэй.
    // Тиймээс add form дээр catalog_item сонголтыг "kind" query-ээр удирдах боломжтой болгож орхино.
    // Хэрэв дараа нь Device дээр тусдаа kind field нэмбэл id_kind-ээр ажиллуулна.

    var kindEl = document.getElementById("id_kind");
    if (!kindEl) return;

    kindEl.addEventListener("change", function () {
      var url = new URL(window.location.href);
      url.searchParams.set("kind", kindEl.value);
      window.location.href = url.toString();
    });
  });
})();
