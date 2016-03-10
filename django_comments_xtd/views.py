from __future__ import unicode_literals

import json
import six

from django.apps import apps
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render_to_response
from django.template import loader, Context, RequestContext
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from django_comments.signals import comment_will_be_posted, comment_was_posted

from django_comments_xtd import get_form, signals, signed
from django_comments_xtd import get_model as get_comment_model
from django_comments_xtd.conf import settings
from django_comments_xtd.models import (TmpXtdComment, 
                                        max_thread_level_for_content_type)
from django_comments_xtd.utils import send_mail


XtdComment = get_comment_model()


def ajax_wrong_request(message, status=400):
    return HttpResponse(json.dumps({'status': status, 'message': message}),
                        content_type='application/json',
                        status=status)

#----------------------------------------------------------------------
def send_email_confirmation_request(
        comment, target, key, 
        text_template="django_comments_xtd/email_confirmation_request.txt", 
        html_template="django_comments_xtd/email_confirmation_request.html"):
    """Send email requesting comment confirmation"""
    subject = _("comment confirmation request")
    confirmation_url = reverse("comments-xtd-confirm", args=[key])
    message_context = Context({ 'comment': comment, 
                                'content_object': target, 
                                'confirmation_url': confirmation_url,
                                'contact': settings.DEFAULT_FROM_EMAIL,
                                'site': Site.objects.get_current() })
    # prepare text message
    text_message_template = loader.get_template(text_template)
    text_message = text_message_template.render(message_context)
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        # prepare html message
        html_message_template = loader.get_template(html_template)
        html_message = html_message_template.render(message_context)
    else: 
        html_message = None

    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL,
              [ comment.user_email, ], html=html_message)


#----------------------------------------------------------------------
def _comment_exists(comment):
    """
    True if exists a XtdComment with same user_name, user_email and submit_date.
    """
    return (XtdComment.objects.filter(
        user_name=comment.user_name, 
        user_email=comment.user_email,
        followup=comment.followup,
        submit_date=comment.submit_date
    ).count() > 0)


#----------------------------------------------------------------------
def _create_comment(tmp_comment):
    """
    Creates a XtdComment from a TmpXtdComment.
    """
    comment = XtdComment(**tmp_comment)
    comment.is_public = True
    comment.save()
    return comment


#----------------------------------------------------------------------
def on_comment_was_posted(sender, comment, request, **kwargs):
    """
    Post the comment if a user is authenticated or send a confirmation email.
    
    On signal django_comments.signals.comment_was_posted check if the 
    user is authenticated or if settings.COMMENTS_XTD_CONFIRM_EMAIL is False. 
    It will post the comment in both cases, otherwise it will send a 
    confirmation email to the email address provided in the comment.
    """
    if settings.COMMENTS_APP != "django_comments_xtd":
        return False

    if (not settings.COMMENTS_XTD_CONFIRM_EMAIL or 
        (comment.user and comment.user.is_authenticated())):
        if not _comment_exists(comment):
            new_comment = _create_comment(comment)
            comment.xtd_comment = new_comment
            notify_comment_followers(new_comment)
    else:
        ctype = request.POST["content_type"]
        object_pk = request.POST["object_pk"]
        model = apps.get_model(*ctype.split(".", 1))
        target = model._default_manager.get(pk=object_pk)
        key = signed.dumps(comment, compress=True, 
                           extra_key=settings.COMMENTS_XTD_SALT)
        send_email_confirmation_request(comment, target, key)

comment_was_posted.connect(on_comment_was_posted)


#----------------------------------------------------------------------
def sent(request):
    comment_pk = request.GET.get("c", None)
    try:
        comment_pk = int(comment_pk)
        comment = XtdComment.objects.get(pk=comment_pk)
    except (TypeError, ValueError, XtdComment.DoesNotExist):
        template_arg = ["django_comments_xtd/posted.html",
                        "comments/posted.html"]
        return render_to_response(template_arg, 
                                  context_instance=RequestContext(request))
    else:
        if (request.is_ajax() and comment.user 
            and comment.user.is_authenticated()):
            template_arg = [
                "django_comments_xtd/%s/%s/comment.html" % (
                    comment.content_type.app_label, 
                    comment.content_type.model),
                "django_comments_xtd/%s/comment.html" % (
                    comment.content_type.app_label,),
                "django_comments_xtd/comment.html"
            ]
            return render_to_response(template_arg, {"comment": comment},
                                      context_instance=RequestContext(request))
        else:
            return redirect(comment)


#----------------------------------------------------------------------
def confirm(request, key, 
            template_discarded="django_comments_xtd/discarded.html"):
    try:
        tmp_comment = signed.loads(str(key), 
                                   extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    if _comment_exists(tmp_comment):
        raise Http404
    # Send signal that the comment confirmation has been received
    responses = signals.confirmation_received.send(sender  = TmpXtdComment,
                                                   comment = tmp_comment,
                                                   request = request
    )
    # Check whether a signal receiver decides to discard the comment
    for (receiver, response) in responses:
        if response == False:
            return render_to_response(template_discarded, 
                                      {'comment': tmp_comment},
                                      context_instance=RequestContext(request))

    comment = _create_comment(tmp_comment)
    notify_comment_followers(comment)
    return redirect(comment)


#----------------------------------------------------------------------
def notify_comment_followers(comment):
    followers = {} 

    previous_comments = XtdComment.objects.filter(
        content_type=comment.content_type,
        object_pk=comment.object_pk, is_public=True,
        followup=True).exclude(user_email=comment.user_email)

    for instance in previous_comments:
        followers[instance.user_email] = (
            instance.user_name, 
            signed.dumps(instance, compress=True,
                         extra_key=settings.COMMENTS_XTD_SALT))

    model = apps.get_model(comment.content_type.app_label,
                           comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    subject = _("new comment posted")
    text_message_template = loader.get_template(
        "django_comments_xtd/email_followup_comment.txt")
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        html_message_template = loader.get_template(
            "django_comments_xtd/email_followup_comment.html")

    for email, (name, key) in six.iteritems(followers):
        mute_url = reverse('comments-xtd-mute', args=[key])
        message_context = Context({ 'user_name': name,
                                    'comment': comment, 
                                    'content_object': target,
                                    'mute_url': mute_url,
                                    'site': Site.objects.get_current() })
        text_message = text_message_template.render(message_context)
        if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
            html_message = html_message_template.render(message_context)
        else:
            html_message = None
        send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, 
                  [ email, ], html=html_message)


#----------------------------------------------------------------------
def reply(request, cid):
    """Get a comment form to reply a comment. It produces a nested comment."""
    try:
        comment = XtdComment.objects.get(pk=cid)
    except (XtdComment.DoesNotExist):
        raise Http404

    if comment.level == max_thread_level_for_content_type(comment.content_type):
        return render_to_response(
            "django_comments_xtd/max_thread_level.html", 
            {'max_level': settings.COMMENTS_XTD_MAX_THREAD_LEVEL},
            context_instance=RequestContext(request))

    form = get_form()(comment.content_object, comment=comment)
    next = request.GET.get("next", reverse("comments-xtd-sent"))
    template_arg = [
        "django_comments_xtd/%s/%s/reply.html" % (
            comment.content_type.app_label,
            comment.content_type.model),
        "django_comments_xtd/%s/reply.html" % (
            comment.content_type.app_label,),
        "django_comments_xtd/reply.html"
    ]
    return render_to_response(template_arg, 
                              {"comment": comment, "form": form, "next": next },
                              context_instance=RequestContext(request))


#----------------------------------------------------------------------
def reply_ajax(request, cid):
    if not request.is_ajax():
        return ajax_wrong_request(_("AJAX call expected."))

    try:
        comment = XtdComment.objects.get(pk=cid)
    except (XtdComment.DoesNotExist):
        raise ajax_wrong_request(_("Comment does not exist."), status=404)

    if comment.level == max_thread_level_for_content_type(comment.content_type):
        raise ajax_wrong_request(_("Reached maximum comment thread level."),
                                 status=403)

    form = get_form()(comment.content_object, comment=comment)
    next_link = request.GET.get("next", reverse("comments-xtd-sent"))
    template_arg = [
        "django_comments_xtd/%s/%s/reply_ajax.html" % (
            comment.content_type.app_label,
            comment.content_type.model),
        "django_comments_xtd/%s/reply_ajax.html" % (
            comment.content_type.app_label,),
        "django_comments_xtd/reply_ajax.html"
    ]
    html = render_to_string(template_arg,
                            {"form": form, "cid": cid, "next": next_link},
                            request=request)
    payload = json.dumps({'status': 'success', 'html': html, 'cid': cid})
    return HttpResponse(payload, content_type='application/json')


#----------------------------------------------------------------------
def mute(request, key):
    try:
        comment = signed.loads(str(key), 
                               extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    if not comment.followup or not _comment_exists(comment):
        raise Http404

    # Send signal that the comment thread has been muted
    signals.comment_thread_muted.send(sender=XtdComment,
                                      comment=comment,
                                      request=request)

    XtdComment.objects.filter(
        content_type=comment.content_type, object_pk=comment.object_pk, 
        is_public=True, followup=True, user_email=comment.user_email
    ).update(followup=False)

    model = apps.get_model(comment.content_type.app_label,
                           comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    
    template_arg = [
        "django_comments_xtd/%s/%s/muted.html" % (
            comment.content_type.app_label, 
            comment.content_type.model),
        "django_comments_xtd/%s/muted.html" % (
            comment.content_type.app_label,),
        "django_comments_xtd/muted.html"
    ]
    return render_to_response(template_arg, 
                              {"content_object": target },
                              context_instance=RequestContext(request))


#----------------------------------------------------------------------
@csrf_protect
@require_POST
def post_comment_ajax(request, next=None, using=None):
    """Post a comment via AJAX.

    HTTP POST is required. If ``POST['submit'] == "preview"`` or if there are
    errors a preview template, ``django_comments_xtd/preview_ajax.html``, will
    be rendered. This function almost mirrors the ``post_comment`` function of 
    ``django_comments.views.comments``.
    """
    if not request.is_ajax():
        return ajax_wrong_request("Bad request, AJAX call expected.")

    data = request.POST.copy()
    if request.user.is_authenticated():
        if not data.get('name', ''):
            data["name"] = request.user.get_full_name() or request.user.get_username()
        if not data.get('email', ''):
            data["email"] = request.user.email

    # Look up the object we're trying to comment about
    ctype = data.get("content_type")
    object_pk = data.get("object_pk")
    if ctype is None or object_pk is None:
        return ajax_wrong_request("Missing content_type or object_pk field.")
    try:
        model = apps.get_model(*ctype.split(".", 1))
        target = model._default_manager.using(using).get(pk=object_pk)
    except (TypeError, LookupError):
        return ajax_wrong_request("Invalid content_type value: %r" %
                                  escape(ctype))
    except AttributeError:
        return ajax_wrong_request(("The given content-type %r does not "
                                   "resolve to a valid model." %
                                   escape(ctype)))
    except ObjectDoesNotExist:
        return ajax_wrong_request(("No object matching content-type %r "
                                   "and object PK %r exists." %
                                   (escape(ctype), escape(object_pk))))
    except (ValueError, ValidationError) as e:
        return ajax_wrong_request(("Attempting go get content-type %r "
                                   "and object PK %r exists raised %s" %
                                   (escape(ctype), escape(object_pk),
                                    e.__class__.__name__)))

    preview = "preview" in data  # want to preview the message?

    # Construct the comment form
    form = get_form()(target, data=data)

    # Check security information
    if form.security_errors():
        return AjaxBadRequest(
            ("The comment form failed security verification: %s" %
             escape(str(form.security_errors()))))

    json_data = {}
    if form.errors:
        json_data.update({'status': 'errors', 'errors': {}})
        field_errors_template_list = [
            ("django_comments_xtd/%s/%s/field_errors.html"
             % (model._meta.app_label, model._meta.model_name)),
            ("django_comments_xtd/%s/field_errors.html" %
             model._meta.app_label),
            "django_comments_xtd/field_errors.html",
        ]
        for field_name in form.errors:
            json_data['errors'][field_name] = render_to_string(
                field_errors_template_list,
                {'field': form[field_name]},
                request=request)
    
    # If there are errors or if we requested a preview show the comment
    if preview or form.errors:
        preview_template_list = [
            ("django_comments_xtd/%s/%s/preview_ajax.html"
             % (model._meta.app_label, model._meta.model_name)),
            ("django_comments_xtd/%s/preview_ajax.html" %
             model._meta.app_label),
            "django_comments_xtd/preview_ajax.html",
        ]
        
        json_data['html'] = render_to_string(
            preview_template_list,
            {"comment": form.data.get("comment", ""),
             "url": form.data.get("url", ""),
             "name": form.data.get("name", ""),
             'form': form},
            request=request)
        if not form.errors:
            json_data['status'] = 'preview'
        return HttpResponse(json.dumps(json_data),
                            content_type='application/json')

    # Otherwise create the comment
    comment = form.get_comment_object()
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    if request.user.is_authenticated():
        comment.user = request.user

    # Signal that the comment is about to be saved
    responses = comment_will_be_posted.send(sender=comment.__class__,
                                            comment=comment,
                                            request=request)

    # Check whether a signal receiver decides to kill the process
    for (receiver, response) in responses:
        if response is False:
            discarded_template_list = [
                ("django_comments_xtd/%s/%s/discarded_ajax.html"
                 % (model._meta.app_label, model._meta.model_name)),
                ("django_comments_xtd/%s/discarded_ajax.html" %
                 model._meta.app_label),
                "django_comments_xtd/discarded_ajax.html",
            ]
            html = render_to_string(discarded_template_list,
                                    {'comment': comment},
                                    request=request)
            payload = json.dumps({'status': 'discarded', 'html': html})
            return HttpResponse(payload, content_type='application/json')
    
    # Save the comment and signal that it was saved
    comment.save()
    comment_was_posted.send(sender=comment.__class__,
                            comment=comment,
                            request=request)

    posted_template_list = [
        ("django_comments_xtd/%s/%s/posted_ajax.html" %
         (model._meta.app_label, model._meta.model_name)),
        ("django_comments_xtd/%s/posted_ajax.html" %
         model._meta.app_label),
        "django_comments_xtd/posted_ajax.html",
    ]
    html = render_to_string(posted_template_list,
                            {'comment': comment},
                            request=request)
    payload = json.dumps({'status': 'posted', 'html': html})
    return HttpResponse(payload, content_type='application/json')
    
