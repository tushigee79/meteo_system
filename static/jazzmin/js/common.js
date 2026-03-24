/* static/inventory/js/common.js */
/* (from old main.js, without dashboard-only chart code) */
(function($) {
    'use strict';

    function setCookie(key, value) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (value * 24 * 60 * 60 * 1000));
        document.cookie = key + '=' + value + ';expires=' + expires.toUTCString() + '; SameSite=Strict;path=/';
    }

    function getCookie(key) {
        const keyValue = document.cookie.match('(^|;) ?' + key + '=("^[^;]*)(;|$)');
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
         Set the currently active menu item.
         */
        const currentUrl = window.location.href.split('#')[0].split('?')[0];

        $('ul.nav-sidebar a').filter(function() {
            return this.href === currentUrl;
        }).each(function() {
            $(this).addClass('active');

            const parent = $(this).parents('li.nav-item').first();
            parent.addClass('menu-open');

            parent.children('a').addClass('active');
        });
    }

    $(document).ready(function () {
        setActiveLinks();
        handleMenu();
    });

})(jQuery);
