/* your custom js go here */

$('.lang-select').change(function(){
    let url = $(this).find(':selected').attr('data-url');
    $('#language').val($(this).val());
    $('#form_lang').submit();
});