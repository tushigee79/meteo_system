/* common.js – shared admin helpers (menu state, active links) */
(function($) {
    'use strict';

    function setCookie(key, value) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (30 * 24 * 60 * 60 * 1000));
        document.cookie = key + '=' + value +
            ';expires=' + expires.toUTCString() +
            '; SameSite=Strict;path=/';
    }

    function getCookie(key) {
        const match = document.cookie.match(new RegExp('(^| )' + key + '=([^;]+)'));
        return match ? match[2] : null;
    }

    function handleMenu() {
        $('[data-widget=pushmenu]').on('click', function () {
            const closed = getCookie('jazzy_menu') === 'closed';
            setCookie('jazzy_menu', closed ? 'open' : 'closed');
        });
    }

    function setActiveLinks() {
        const currentUrl = window.location.href.split('#')[0].split('?')[0];

        $('ul.nav-sidebar a').each(function() {
            if (this.href === currentUrl) {
                $(this).addClass('active');
                const parent = $(this).parents('li.nav-item').first();
                parent.addClass('menu-open');
                parent.children('a').addClass('active');
            }
        });
    }

    $(function () {
        setActiveLinks();
        handleMenu();
    });

})(jQuery);