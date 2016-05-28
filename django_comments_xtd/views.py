from __future__ import unicode_literals

import json
import six

from django.apps import apps
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render_to_response
from django.template import loader, Context, RequestContext
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.text import unescape_entities
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from django_comments.signals import comment_will_be_posted, comment_was_posted
from django_comments.views.utils import next_redirect

from django_comments_xtd import get_form, signals, signed
from django_comments_xtd import get_model as get_comment_model
from django_comments_xtd.forms import FollowUpForm
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
    context = {'comment': comment,
               'content_object': target,
               'confirmation_url': confirmation_url,
               'contact': settings.DEFAULT_FROM_EMAIL,
               'site': Site.objects.get_current()}
    # prepare text message
    text_message_template = loader.get_template(text_template)
    text_message = unescape_entities(text_message_template.render(context))
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        # prepare html message
        html_message_template = loader.get_template(html_template)
        html_message = html_message_template.render(context)
    else: 
        html_message = None

    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL,
              [ comment.user_email, ], html=html_message)


#----------------------------------------------------------------------
def _comment_exists(comment):
    """
    True if a XtdComment exists with same user_name, user_email and submit_date.
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
            if comment.is_public:
                notify_comment_followers(new_comment,
                                         is_secure=request.is_secure())
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
        pending_template = "django_comments_xtd/pending.html"
        if request.is_ajax():
            json_data = {'status': 'pending',
                         'html': render_to_string(pending_template,
                                                  request=request)}
            return HttpResponse(json.dumps(json_data),
                                content_type='application/json')
        else:
            return render_to_response(pending_template, 
                                      context_instance=RequestContext(request))
    else:
        if (request.is_ajax()
            and comment.user 
            and comment.user.is_authenticated()):
            if comment.is_public:
                payload = json.dumps({'status': 'posted',
                                      'url': comment.get_absolute_url()})
                return HttpResponse(payload, content_type='application/json')
            else:
                template = 'django_comments_xtd/moderated_ajax.html'
                html = render_to_string(template, {"comment": comment},
                                        request=request)
                payload = json.dumps({'status': 'moderated', 'html': html})
                return HttpResponse(payload, content_type='application/json')
        else:
            if comment.is_public:
                return redirect(comment)
            else:
                return render_to_response(
                    "django_comments_xtd/moderated.html",
                    {'comment': comment},
                    context_instance=RequestContext(request))


#----------------------------------------------------------------------
def confirm(request, key, 
            template_discarded="django_comments_xtd/discarded.html",
            template_moderated="django_comments_xtd/moderated.html"):
    try:
        tmp_comment = signed.loads(str(key), 
                                   extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    if _comment_exists(tmp_comment):
        raise Http404
    # Send signal that the comment confirmation has been received
    responses = signals.confirmation_received.send(sender=TmpXtdComment,
                                                   comment=tmp_comment,
                                                   request=request
    )
    # Check whether a signal receiver decides to discard the comment
    for (receiver, response) in responses:
        if response == False:
            return render_to_response(template_discarded, 
                                      {'comment': tmp_comment},
                                      context_instance=RequestContext(request))

    comment = _create_comment(tmp_comment)
    if comment.is_public is False:
        return render_to_response(template_moderated, 
                                  {'comment': comment},
                                  context_instance=RequestContext(request))
    else:
        notify_comment_followers(comment, is_secure=request.is_secure())
        return redirect(comment)


#----------------------------------------------------------------------
def notify_comment_followers(comment, is_secure=False):
    followers = {} 

    kwargs = {'content_type': comment.content_type,
              'object_pk': comment.object_pk,
              'thread_id': comment.thread_id,
              'is_public': True,
              'followup': True}
    previous_comments = XtdComment.objects\
                                  .filter(**kwargs)\
                                  .exclude(user_email=comment.user_email)

    for item in previous_comments:
        followup_payload = "%s;%020d" % (item.user_email, item.id)
        followup_sign = signed.dumps(followup_payload, compress=True,
                                     extra_key=settings.COMMENTS_XTD_SALT)
        checkout_payload = "%s;%020d" % (item.user_email, comment.id)
        checkout_sign = signed.dumps(checkout_payload, compress=True,
                                     extra_key=settings.COMMENTS_XTD_SALT)
        followers[item.user_email] = (item.user_name,
                                      followup_sign,
                                      checkout_sign)

    model = apps.get_model(comment.content_type.app_label,
                           comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    subject = _("new comment posted")
    text_message_template = loader.get_template(
        "django_comments_xtd/email_followup_comment.txt")
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        html_message_template = loader.get_template(
            "django_comments_xtd/email_followup_comment.html")

    for email, (name, followup_sign, checkout_sign) in six.iteritems(followers):
        followup_url = reverse('comments-xtd-followup', args=[followup_sign])
        checkout_url = reverse('comments-xtd-checkout', args=[checkout_sign])
        context = {'user_name': name,
                   'comment': comment, 
                   'content_object': target,
                   'followup_url': followup_url,
                   'checkout_url': checkout_url,
                   'site': Site.objects.get_current(),
                   'schema': 'https' if is_secure else 'http'}
        text_message = unescape_entities(text_message_template.render(context))
        if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
            html_message = html_message_template.render(context)
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
@csrf_protect
def followup(request, key):
    """Allows the user to change the follow-up switch of a comment."""
    try:
        payload = signed.loads(str(key),
                               extra_key=settings.COMMENTS_XTD_SALT)
        user_email, comment_id = payload.split(';')
        comment = XtdComment.objects.get(pk=int(comment_id))
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    # I'm commenting the following two lines because otherwise the mute link
    # doesn't work as a switch to turn on/off notifications.
    # if not comment.followup or not _comment_exists(comment):
    #     raise Http404

    model = apps.get_model(comment.content_type.app_label,
                           comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    
    if comment.user_email != user_email:  # Rare but may happen
        raise Http404

    if request.method == 'GET':
        template_arg = ["django_comments_xtd/%s/%s/change_followup.html"
                        % (comment.content_type.app_label,
                           comment.content_type.model),
                        "django_comments_xtd/%s/change_followup.html"
                        % (comment.content_type.app_label,),
                        "django_comments_xtd/change_followup.html"]
        form = FollowUpForm(comment=comment, initial={'key':key})
        return render_to_response(template_arg,
                                  {"comment": comment,
                                   "content_object": target,
                                   "form": form,
                                   "key": key},
                                  context_instance=RequestContext(request))

    elif request.method == 'POST':
        form = FollowUpForm(request.POST, comment=comment)
        if form.is_valid():
            if form.cleaned_data.get('key', None) != key:
                raise Http404
        else:
            raise Http404

        if form.cleaned_data['followup'] != comment.followup:
        # Send signal to indicate that the comment changed its followup setting
            signals.comment_followup_toggled.send(sender=XtdComment,
                                                  comment=comment,
                                                  request=request)
            XtdComment.objects.filter(pk=int(comment_id))\
                              .update(followup=form.cleaned_data['followup'])
    
        template_arg = ["django_comments_xtd/%s/%s/change_followup_posted.html"
                        % (comment.content_type.app_label, 
                           comment.content_type.model),
                        "django_comments_xtd/%s/change_followup_posted.html"
                        % (comment.content_type.app_label,),
                        "django_comments_xtd/change_followup_posted.html"]
        return render_to_response(template_arg, 
                                  {"comment": comment,
                                   "content_object": target,
                                   "followup": form.cleaned_data['followup']},
                                  context_instance=RequestContext(request))


def checkout(request, key):
    """Pre-confirm a potential answer with a cookie while visiting comment.
    
    The URL that brings to this view has been delivered to the user in an email
    as a follow-up notification. By clicking the link the user is redirected to
    the comment while receiving in the response a cookie that will validate a 
    potential answer to the comment. This prevent the user from having to
    confirm her email address again for a 2nd or subsequent comments posted to 
    the same object.
    """
    try:
        payload = signed.loads(str(key),
                               extra_key=settings.COMMENTS_XTD_SALT)
        _, comment_id = payload.split(';')
        comment = XtdComment.objects.get(pk=int(comment_id))
        print("I got the comment")
    except (ValueError, signed.BadSignature):
        raise Http404
    return HttpResponseRedirect(comment.get_absolute_url())

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
        return ajax_wrong_request(
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
            payload = json.dumps({'status': 'discarded',
                                  'url': reverse('comments-xtd-discarded')})
            response = HttpResponse(payload, content_type='application/json')
            key = signed.dumps(comment, compress=True, 
                               extra_key=settings.COMMENTS_XTD_SALT)
            response.set_cookie('discarded', key, max_age=30)
            return response
    
    # Save the comment and signal that it was saved
    comment_was_posted.send(sender=comment.__class__,
                            comment=comment,
                            request=request)

    return next_redirect(request, fallback=next or 'comments-comment-done',
                         c=comment._get_pk_val())    


def discarded(request):
    if not 'discarded' in request.COOKIES:
        raise Http404
    try:
        tmp_comment = signed.loads(request.COOKIES['discarded'],
                                   extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    else:
        discarded_template_list = [
            ("django_comments_xtd/%s/%s/discarded.html"
             % (tmp_comment.content_type.app_label,
                tmp_comment.content_type.model)),
            ("django_comments_xtd/%s/discarded.html" %
             tmp_comment.content_type.app_label),
            "django_comments_xtd/discarded.html",
        ]
        response = render_to_response(discarded_template_list, 
                                      {'comment': tmp_comment},
                                      context_instance=RequestContext(request))
        response.delete_cookie('discarded')
        return response
