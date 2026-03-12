(function($) {
    'use strict';
    
    // Энэ функц нь сумдын жагсаалтыг шинэчилнэ
    function updateSumList(aimagId) {
        var sumField = $('#id_sum_ref');
        
        // Сумыг цэвэрлэх
        sumField.empty().append('<option value="">---------</option>');
        
        if (aimagId) {
            var url = '/inventory/ajax/load-sums/';
            
            $.getJSON(url, { 'parent_id': aimagId }, function(data) {
                $.each(data, function(index, item) {
                    sumField.append($('<option>', { 
                        value: item.id, 
                        text: item.name 
                    }));
                });
                
                // Select2 ашиглаж байгаа бол UI-г шинэчлэх
                if (sumField.data('select2') || sumField.hasClass('select2-hidden-accessible')) {
                    sumField.trigger('change.select2');
                }
            });
        } else {
            if (sumField.data('select2') || sumField.hasClass('select2-hidden-accessible')) {
                sumField.trigger('change.select2');
            }
        }
    }

    $(document).ready(function() {
        // 1. Ердийн change эвент (Back-up)
        $(document).on('change', '#id_aimag_ref', function() {
            updateSumList($(this).val());
        });

        // 2. Select2-т зориулсан тусгай эвент (Хамгийн чухал нь)
        $('#id_aimag_ref').on('select2:select', function (e) {
            updateSumList(e.params.data.id);
        });
    });
})(django.jQuery || jQuery);