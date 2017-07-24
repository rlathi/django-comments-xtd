from django.contrib.contenttypes.models import ContentType

from django_comments.views.moderation import perform_flag
from rest_framework import generics, mixins, permissions, status
from rest_framework.response import Response

from django_comments_xtd import views
from django_comments_xtd.api import serializers
from django_comments_xtd.models import XtdComment
from rest_framework.views import APIView


class CommentCreate(generics.CreateAPIView):
    """Create a comment."""
    serializer_class = serializers.WriteCommentSerializer

    def post(self, request, *args, **kwargs):
        response = super(CommentCreate, self).post(request, *args, **kwargs)
        if self.resp_dict['code'] == 201:  # The comment has been created.
            return response
        elif self.resp_dict['code'] in [202, 204, 403]:
            return Response(status=self.resp_dict['code'])

    def perform_create(self, serializer):
        self.resp_dict = serializer.save()


class CommentList(generics.ListAPIView):
    """List all comments for a given ContentType and object ID."""
    serializer_class = serializers.ReadCommentSerializer

    def get_queryset(self):
        content_type_arg = self.kwargs.get('content_type', None)
        object_pk_arg = self.kwargs.get('object_pk', None)
        app_label, model = content_type_arg.split("-")
        try:
            content_type = ContentType.objects.get_by_natural_key(app_label,
                                                                  model)
        except ContentType.DoesNotExist:
            qs = XtdComment.objects.none()
        else:
            qs = XtdComment.objects.filter(content_type=content_type,
                                           object_pk=int(object_pk_arg),
                                           is_public=True)
        return qs


class CommentCount(generics.GenericAPIView):
    """Get number of comments posted to a given ContentType and object ID."""
    serializer_class = serializers.ReadCommentSerializer

    def get_queryset(self):
        content_type_arg = self.kwargs.get('content_type', None)
        object_pk_arg = self.kwargs.get('object_pk', None)
        app_label, model = content_type_arg.split("-")
        content_type = ContentType.objects.get_by_natural_key(app_label, model)
        qs = XtdComment.objects.filter(content_type=content_type,
                                       object_pk=int(object_pk_arg),
                                       is_public=True)
        return qs

    def get(self, request, *args, **kwargs):
        return Response({'count': self.get_queryset().count()})


class ToggleFeedbackFlag(generics.CreateAPIView, mixins.DestroyModelMixin):
    """Create and delete like/dislike flags."""

    serializer_class = serializers.FlagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def post(self, request, *args, **kwargs):
        response = super(ToggleFeedbackFlag, self).post(request, *args,
                                                        **kwargs)
        if self.created:
            return response
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        f = getattr(views, 'perform_%s' % self.request.data['flag'])
        self.created = f(self.request, serializer.validated_data['comment'])


class CreateReportFlag(generics.CreateAPIView):
    """Create 'removal suggestion' flags."""

    serializer_class = serializers.FlagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def post(self, request, *args, **kwargs):
        return super(CreateReportFlag, self).post(request, *args, **kwargs)

    def perform_create(self, serializer):
        perform_flag(self.request, serializer.validated_data['comment'])

class ApiCommentsView(APIView):

    def get(self, request, *args, **kwargs):
        context = {}
        content_type_arg = self.kwargs.get('content_type', None)
        object_pk_arg = self.kwargs.get('object_pk', None)
        qs = XtdComment.objects.filter(content_type__pk=13,
                                           object_pk=int(object_pk_arg),
                                           is_public=True)
        comments = tree_from_queryset(request, qs, True, True, self.request.user)
        context['comments'] = comments

        return Response(context)

def tree_from_queryset(request, qs, with_flagging=False,
                       with_feedback=False, user=None):

    """Converts a XtdComment queryset into a list of nested dictionaries.
    The queryset has to be ordered by thread_id, order.
    Each dictionary contains two attributes::
        {
            'comment': the comment object itself,
            'children': [list of child comment dictionaries]
        }
    """
    def get_user_feedback(comment, user):
        d = {'likedit_users': comment.users_flagging("I liked it"),
             'dislikedit_users': comment.users_flagging("I disliked it")}
        if user is not None:
            if user in d['likedit_users']:
                d['likedit'] = True
            if user in d['dislikedit_users']:
                d['dislikedit'] = True
        return d

    def add_children(children, obj, user):
        for item in children:
            if item['comment']['id'] == obj.parent_id:
                obj_api = serializers.ReadCommentSerializer(obj, context={'request': request}).data
                child_dict = {'comment': obj_api, 'children': []}
                item['children'].append(child_dict)
                return True
            elif item['children']:
                if add_children(item['children'], obj, user):
                    return True
        return False

    def get_new_dict(obj):
        obj_api = serializers.ReadCommentSerializer(obj, context={'request': request}).data
        new_dict = {'comment': obj_api, 'children': []}
        if with_flagging:
            users_flagging = obj.users_flagging("removal suggestion")
            if user.has_perm('django_comments.can_moderate'):
                new_dict.update({'flagged_count': len(users_flagging)})
            new_dict.update({'flagged': user in users_flagging})
        return new_dict

    dic_list = []
    cur_dict = None
    for obj in qs:
        if cur_dict and obj.level == cur_dict['comment']['level']:
            dic_list.append(cur_dict)
            cur_dict = None
        if not cur_dict:
            cur_dict = get_new_dict(obj)
            continue
        if obj.parent_id == cur_dict['comment']['id']:
            child_dict = get_new_dict(obj)
            cur_dict['children'].append(child_dict)
        else:
            add_children(cur_dict['children'], obj, user)
    if cur_dict:
        dic_list.append(cur_dict)
    return dic_list
