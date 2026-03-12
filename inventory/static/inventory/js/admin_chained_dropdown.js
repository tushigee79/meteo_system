// inventory/static/inventory/js/admin_chained_dropdown.js
(function($) {
    $(document).ready(function() {
        // Django Admin-ийн Аймаг болон Сум талбарууд
        var aimagField = $('#id_aimag_ref'); 
        var sumField = $('#id_sum_ref');

        aimagField.change(function() {
            var aimagId = $(this).val();
            var url = "/ajax/load-sums/"; // Таны urls.py дээрх зам

            if (aimagId) {
                $.ajax({
                    url: url,
                    data: { 'aimag_ref': aimagId },
                    success: function(data) {
                        sumField.html(data); // HTML <option>-уудыг шууд орлуулна
                    }
                });
            } else {
                sumField.html('<option value="">---------</option>');
            }
        });
    });
})(django.jQuery || jQuery);