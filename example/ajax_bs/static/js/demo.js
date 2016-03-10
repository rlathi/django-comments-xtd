function _showFieldsOnFocus(selector) {
  selector.find('textarea').on('focus', function() {
    selector.find('.visible-on-focus').fadeIn(150);
  });
}

function replyClickSuccessCallback(data) {
  if(data.status=='success') {
    $('a[data-comment-id='+data.cid+']').after(data.html);
    _showFieldsOnFocus(
      $('FORM[data-comment-id='+data.cid+']')
    );
  } else if(data.status=='unchanged') {
    $('DIV[data-reply-div='+data.cid+']').toggle();
  }
}

function replyClickErrorCallback(data) {
  window.location.href = data.elem.href;
}

function cleanPreviousState($form) {
  $form.find('*[data-comment-element=preview]')
    .html('')
    .addClass('hidden');
  $form.find('*[data-comment-element=errors]')
    .html('')
    .addClass('hidden');
  $form.find('.has-error')
    .removeClass('has-error');
  $form.find('*[data-comment-element=field-errors]').remove();
}

function postSuccessCallback(data) {
  var $form = $(this.target);
  cleanPreviousState($form);
  if(data.status=='preview')
  {
    $form.find('*[data-comment-element=preview]')
      .html(data.html)
      .removeClass('hidden');
  }
  else if(data.status=='discarded')
  {
    $form.find('*[data-comment-element=preview]')
      .html(data.html)
      .removeClass('hidden');
  }
  else if(data.status=='errors')
  {
    $form.find('*[data-comment-element=errors]')
      .html('Correct the errors below.')
      .removeClass('hidden');
    for(var field_name in data.errors) {
      var field = $(this.target.elements[field_name]);
      field.parents('.form-group').addClass('has-error');
      if(field.parent().find('.help-block').length==0) {
        field.parent().append(data.errors[field_name]);
      }
    }
  }
}

function postErrorCallback(xhr, status, errorThrown) {
  var $form = $(this.target);
  cleanPreviousState($form);
  $form.find('*[data-comment-element=errors]')
    .html(xhr.responseJSON.message)
    .removeClass('hidden');
}
