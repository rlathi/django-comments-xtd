"""
Signals relating to django-comments-xtd.
"""
from django.dispatch import Signal

# Sent just after a comment has been verified.
confirmation_received = Signal(providing_args=["comment", "request"])

# Sent just after a user toggled the follow-up switch of a comment.
comment_followup_toggled = Signal(providing_args=["comment", "requests"])
