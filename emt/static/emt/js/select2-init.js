// emt/js/select2-init.js
$(document).ready(function () {
    $('.select2-ajax').select2({
        theme: 'bootstrap4',
        width: '100%',
        placeholder: 'Type to search...',
        allowClear: true,
        ajax: {
            url: $('.select2-ajax').data('url'),
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {q: params.term};
            },
            processResults: function (data) {
                return {results: data};
            },
            cache: true
        }
    });
});
