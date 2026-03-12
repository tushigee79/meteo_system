(function($) {
    $(function() {
        const $aimag = $("#id_admin_aimag");
        const $sum = $("#id_admin_sum");
        const $location = $("#id_location");

        if (!$aimag.length || !$sum.length || !$location.length) {
            return;
        }

        const loadSumsUrl = window.location.pathname.replace(/\/change\/$/, "/").replace(/\/add\/$/, "/") + "ajax/load-sums/";
        const loadLocationsUrl = window.location.pathname.replace(/\/change\/$/, "/").replace(/\/add\/$/, "/") + "ajax/location-options/";

        function refillSelect($select, items, selectedValue, emptyLabel) {
            $select.empty();
            $select.append(new Option(emptyLabel || "---------", ""));
            items.forEach(function(item) {
                const option = new Option(item.name, item.id, false, String(item.id) === String(selectedValue));
                $select.append(option);
            });
        }

        function loadSums(selectedSumId, callback) {
            const aimagId = $aimag.val();
            const currentSum = selectedSumId || $sum.val();

            if (!aimagId) {
                refillSelect($sum, [], "", "---------");
                if (callback) callback();
                return;
            }

            $.getJSON(loadSumsUrl, { aimag_id: aimagId })
                .done(function(data) {
                    refillSelect($sum, data.results || [], currentSum, "---------");
                    if (callback) callback();
                })
                .fail(function() {
                    refillSelect($sum, [], "", "---------");
                    if (callback) callback();
                });
        }

        function loadLocations(selectedLocationId) {
            const aimagId = $aimag.val();
            const sumId = $sum.val();
            const currentLocation = selectedLocationId || $location.val();

            $.getJSON(loadLocationsUrl, {
                aimag_id: aimagId,
                sum_id: sumId
            })
            .done(function(data) {
                refillSelect($location, data.results || [], currentLocation, "---------");
            })
            .fail(function() {
                refillSelect($location, [], "", "---------");
            });
        }

        const initialSum = $sum.val();
        const initialLocation = $location.val();

        if ($aimag.val()) {
            loadSums(initialSum, function() {
                loadLocations(initialLocation);
            });
        }

        $aimag.on("change", function() {
            refillSelect($sum, [], "", "---------");
            refillSelect($location, [], "", "---------");

            loadSums("", function() {
                loadLocations("");
            });
        });

        $sum.on("change", function() {
            loadLocations("");
        });
    });
})(django.jQuery);