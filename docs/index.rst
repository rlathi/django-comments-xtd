.. django-comments-xtd documentation master file, created by
   sphinx-quickstart on Mon Dec 19 19:20:12 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

django-comments-xtd
===================

**django-comments-xtd** is a complete commenting application for the Django Web Framework offering the following set of features:

.. index::
   single: Features

1. Comments can be nested up to a customizable maximum thread level.
2. Users can opt-in to receive notifications of follow-up comments via email.
3. Notifications arrive with a link to toggle follow-up comments at will.
4. Comment confirmation via email when users are not authenticated.
5. Follow-up notification links allow users to skip further confirmation by email.
6. Comments hit the database only after users, when not authenticated, confirm them by email.
7. Template tags to list/render the last N comments posted to any given list of app.model pairs.
8. Moderation view included, so that moderators can quickly approve/reject pending comments.
9. Comments can be flagged so that moderation is requested for such comments.
10. AJAX client interactions performed through included jQuery plugin.  
11. Emails are queued and sent with a separated process.
12. A basic editor or a `ProseMirror <https://prosemirror.net>`_ editor.

See the features in action in the `live demo <https://www.swedrux.com/django-comments-xtd/demo/>`_.
    
.. toctree::
   :maxdepth: 2

   example
   tutorial
   templatetags
   extending
   settings
   templates


.. index::
   pair: Quick; Start

Quick start
===========

1. In your ``settings.py``:

 * Add ``django.contrib.comments`` and ``django_comments_xtd`` to ``INSTALLED_APPS``
 * Add ``COMMENTS_APP = "django_comments_xtd"``
 * Add ``COMMENTS_XTD_MAX_THREAD_LEVEL = N``, being ``N`` the maximum level up to which comments can be threaded:

  * When N = 0: comments are not nested
  * When N = 1: comments can be bested at level 0
  * When N = K: comments can be nested up until level K-1

  This setting can also be set up on a per ``<app>.<model>`` basis so that you can enable different thread levels for different models. ie: no nested comment for blog posts, up to one thread level for book reviews...

  Read more about ``COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL`` in the :doc:`tutorial` and see it in action in the **multiple** demo site in :doc:`example`.

 * Customize your project's email settings:

  * ``EMAIL_HOST = "smtp.mail.com"``
  * ``EMAIL_PORT = "587"``
  * ``EMAIL_HOST_USER = "alias@mail.com"``
  * ``EMAIL_HOST_PASSWORD = "yourpassword"``
  * ``DEFAULT_FROM_EMAIL = "Helpdesk <helpdesk@yourdomain>"``

2. If you want to allow comments written in markup languages like Markdown or reStructuredText:

 * Get the dependencies: `django-markup <https://github.com/bartTC/django-markup>`_
 * And add ``django_markup`` to ``INSTALLED_APPS``

3. Add ``url(r'^comments/', include('django_comments_xtd.urls'))`` to your root URLconf.

4. Change templates to introduce comments:

 * Load the ``comments`` templatetag and use their tags (ie: in your ``templates/app/model_detail.html`` template):

  * ``{% get_comment_count for object as comment_count %}``
  * ``{% render_comment_list for object %}`` (uses ``comments/list.html``)
  * ``{% render_comment_form for post %}`` (uses ``comments/form.html`` and ``comments/preview.html``)

 * Load the ``comments_xtd`` templatetag and use their tags and filter:

  * ``{% get_xtdcomment_count as comments_count for blog.story blog.quote %}``
  * ``{% render_last_xtdcomments 5 for blog.story blog.quote using "blog/comment.html" %}``
  * ``{% get_last_xtdcomments 5 as last_comments for blog.story blog.quote %}``
  * Filter render_markup_comment: ``{{ comment.comment|render_markup_comment }}``. You may want to copy and change the template ``comments/list.html`` from ``django.contrib.comments`` to use this filter.

5. ``syncdb``, ``runserver``, and

6. Hit your App's URL!

7. Have questions? Keep reading, and look at the 3 demo sites.


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
