$(document).ready(function() {
    $("#id_aimag_ref").change(function() {
        const aimagId = $(this).val();
        const aimagText = $("#id_aimag_ref option:selected").text();
        
        // 1. Байгууллагыг автоматаар оноох
        if (aimagId && aimagText !== "---------") {
            const targetOrgName = aimagText + " УЦУОШТ";
            $("#id_owner_org option").each(function() {
                if ($(this).text().trim() === targetOrgName) {
                    $(this).prop('selected', true);
                }
            });
        }

        // 2. Сумдыг динамикаар ачаалах
        $.ajax({
            url: "/inventory/ajax/load-sums/",
            data: { 'aimag_id': aimagId },
            success: function(data) {
                let html = '<option value="">---------</option>';
                data.forEach(function(item) {
                    html += `<option value="${item.id}">${item.name}</option>`;
                });
                $("#id_sum_ref").html(html);
            }
        });
    });
});