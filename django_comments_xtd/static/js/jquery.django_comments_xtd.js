/*
 * jquery.django_comments_xtd.js
 * https://github.com/danirus/django-comments-xtd
 *
 * Copyright (c) 2016 Daniel Rus Morales
 * Licensed under the MIT License.
 */
(function($) {
  var settings;
  var $commentsXtd;

  $.fn.commentsXtd = function(opts) {
    settings = $.extend({}, $.fn.commentsXtd.opts, opts);
    $commentsXtd = this;
    initReplyLinks($commentsXtd);
    initForm($commentsXtd.find('FORM[data-comment-id=main]'));
    return this;
  }

  function setClicked() {
    clicked = this.name;
  }
  
  function loadReplyForm(cid, elem) {
    $.ajax({
      url: settings.replyClickURL.replace(/0/, cid),
      cache: false
    }).done(function(data) {
      data.elem = elem;
      settings.replyClickSuccessCallback(data);
      initForm($('FORM[data-comment-id='+cid+']'));
    }).error(function(xhr, status, errorThrown) {
      data = {status:'error', elem:elem, xhr:xhr, errorThrown:errorThrown};
      settings.replyClickErrorCallback(data);
    });
  }

  function submitForm(event) {
    event.preventDefault();
    var $form = $(event.target);
    var datacid = $form.attr('data-comment-id');
    var preview = (clicked == 'preview');
    var postaction = $form.attr('action') || './';
    var ajaxaction = $form.attr('data-ajax-action');
    var data = $form.serialize() + (preview ? '&preview=1' : '');
    $.ajax({
      type: 'POST',
      url: ajaxaction || postaction,
      data: data,
      dataType: 'json',
      success: function(data) {
        if(data.status=='discarded') {
          window.location.href = settings.discardedURL;
        } else {
	      settings.postSuccessCallback.call(event, data);
        }
      },
      error: function(xhr, status, errorThrown) {
        settings.postErrorCallback.call(event, xhr, status, errorThrown);
      }
    });
  }

  function initReplyLinks(elem) {
    elem.find('*[data-comment-element=replylink]').click(function(event) {
      event.preventDefault();
      $link = event.target;
      var cid = $link.dataset.commentId;
      if($('FORM[data-comment-id='+cid+']').length==0) {
        loadReplyForm(cid, $link);
      } else {
        if(settings.replyClickSuccessCallback != null) {
          settings.replyClickSuccessCallback({
            status: 'unchanged',
            html: '',
            cid: cid,
            elem: this
          });
        }
      }
      return false;
    });
  }
  
  function initForm(form) {
    form.find('input[type=submit]')
	  .focus(setClicked)
	  .mousedown(setClicked)
	  .click(setClicked);
    form.submit(submitForm);
  };

  $.fn.commentsXtd.opts = {
    postURL: '',
    postSuccessCallback: function(data) {},
    postErrorCallback: function(data) {},
    replyClickURL: '',
    replyClickSuccessCallback: function(data) {},
    replyClickErrorCallback: function(data) {}
  };  
  
})(jQuery);
