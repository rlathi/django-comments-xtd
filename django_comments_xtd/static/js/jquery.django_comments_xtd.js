/*
 * jquery.django_comments_xtd.js
 * https://github.com/danirus/django-comments-xtd
 *
 * Copyright (c) 2016 Daniel Rus Morales
 * Licensed under the MIT License.
 */
(function($) {
  var $comments;
  var old = $.fn.comments;
  
  $.fn.comments = function(opts) {
    $.fn.comments.config = $.extend({}, $.fn.comments.opts, opts);
    $comments = this;
    initReplyLinks($comments);
    initForm($comments.find('FORM[data-comment-id="main"]'));
    return this;
  }

  $.fn.comments.config = null;

  $.fn.comments.opts = {
    onPostCommentSuccess: function(data) {},
    onPostCommentError: function(data) {},
    replyClickURL: '',
    onReplyClickSuccess: function(data) {},
    onReplyClickError: function(data) {}
  };  
  
  function setClicked() {
    clicked = this.name;
  }
  
  function loadReplyForm() {
    var link = this;
    var cid = link.dataset.commentId;
    $.ajax({
      url: $.fn.comments.config.replyClickURL.replace(/0/, cid),
      cache: false
    }).done(function(data) {
      $.fn.comments.config.onReplyClickSuccess.call(link, data);
      initForm($('FORM[data-comment-id="'+cid+'"]'));
    }).error(function(xhr, status, errorThrown) {
      data = {status:'error', xhr:xhr, errorThrown:errorThrown};
      $.fn.comments.config.onReplyClickError.call(link, data);
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
          window.location.href = data.url;
        } else if(data.status=='posted') {          
          window.location.href = data.url;
        } else {
	      $.fn.comments.config.onPostCommentSuccess.call(event, data);
        }
      },
      error: function(xhr, status, errorThrown) {
        $.fn.comments.config.onPostCommentError.call(event, xhr, status, errorThrown);
      }
    });
  }

  function initReplyLinks(target) {
    target.find('[data-comment-element="replylink"]').click(function(event) {
      event.preventDefault();
      link = event.target;
      var cid = link.dataset.commentId;
      if($('FORM[data-comment-id="'+cid+'"]').length==0) {
        loadReplyForm.call(link);
      } else {
        if($.fn.comments.config.onReplyClickSuccess != null) {
          $.fn.comments.config.onReplyClickSuccess.call(
            link, {status: 'unchanged', cid: cid})
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

  //----------------------------------------------------------------------
  // NoConflict
  $.fn.comments.noConflict = function() {
    $.fn.comments = old;
    return this;
  };
  
})(jQuery);
