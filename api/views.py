from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import User, Workspace, WorkspaceMember, Document, DocumentVersion, Comment, Tag, AuditLog
from .serializers import (
    UserSerializer, WorkspaceSerializer, WorkspaceMemberSerializer,
    DocumentSerializer, DocumentVersionSerializer, CommentSerializer,
    TagSerializer, AuditLogSerializer,
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def retrieve(self, request, *args, **kwargs):
        try:
            user = User.objects.get(pk=kwargs['pk'])
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(user).data)

class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.select_related('owner').annotate(member_count=Count('members', distinct=True))
    serializer_class = WorkspaceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        owner_id = request.data.get('owner')
        try:
            owner = User.objects.get(pk=owner_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Owner user does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                workspace = Workspace.objects.create(
                    name=serializer.validated_data['name'],
                    owner=owner,
                    is_active=serializer.validated_data.get('is_active', True),
                )
                WorkspaceMember.objects.create(
                    workspace=workspace,
                    user=owner,
                    role=WorkspaceMember.Role.ADMIN,
                )
                # Demo-only failure switch: proves the whole atomic block rolls back.
                if serializer.validated_data.get('simulate_failure', False):
                    WorkspaceMember.objects.create(
                        workspace=workspace,
                        user=owner,
                        role=WorkspaceMember.Role.ADMIN,
                    )
        except IntegrityError:
            return Response({'detail': 'Workspace could not be created because of a database integrity error.'}, status=status.HTTP_409_CONFLICT)

        workspace = Workspace.objects.select_related('owner').annotate(member_count=Count('members', distinct=True)).get(pk=workspace.pk)
        return Response(self.get_serializer(workspace).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        try:
            workspace = Workspace.objects.select_related('owner').annotate(
                member_count=Count('members', distinct=True)
            ).get(pk=kwargs['pk'])
        except Workspace.DoesNotExist:
            return Response({'detail': 'Workspace not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(workspace).data)

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        workspace = Workspace.objects.select_related('owner').filter(pk=pk).first()
        if not workspace:
            return Response({'detail': 'Workspace not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            qs = WorkspaceMember.objects.select_related('user', 'workspace').filter(workspace_id=pk)
            roles = request.query_params.get('role')
            if roles:
                qs = qs.filter(role__in=[r.strip() for r in roles.split(',') if r.strip()])
            return Response(WorkspaceMemberSerializer(qs, many=True).data)

        user_id = request.data.get('user')
        role = request.data.get('role')
        if role not in WorkspaceMember.Role.values:
            return Response({'detail': 'Role must be one of: admin, editor, viewer.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            member = WorkspaceMember.objects.create(workspace=workspace, user=user, role=role)
        except IntegrityError:
            return Response({'detail': 'User is already a member of this workspace.'}, status=status.HTTP_409_CONFLICT)
        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        workspace = Workspace.objects.filter(pk=pk).first()
        if not workspace:
            return Response({'detail': 'Workspace not found.'}, status=status.HTTP_404_NOT_FOUND)
        doc_stats = workspace.documents.aggregate(total=Count('id', distinct=True))
        comment_stats = Comment.objects.filter(document__workspace=workspace).aggregate(total=Count('id', distinct=True))
        member_stats = workspace.members.aggregate(total=Count('id', distinct=True))
        return Response({
            'workspace_id': str(workspace.id),
            'document_count': doc_stats['total'] or 0,
            'member_count': member_stats['total'] or 0,
            'total_comments': comment_stats['total'] or 0,
        })

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related('workspace', 'created_by').prefetch_related('tags')
    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.select_related('workspace', 'created_by').prefetch_related('tags')
        workspace = self.request.query_params.get('workspace')
        status_param = self.request.query_params.get('status')
        tag = self.request.query_params.get('tag')
        search = self.request.query_params.get('search')
        status_list = [s.strip() for s in status_param.split(',')] if status_param else []
        workspace_list = [w.strip() for w in workspace.split(',')] if workspace else []
        if workspace_list:
            qs = qs.filter(workspace__in=workspace_list)
        if status_list:
            qs = qs.filter(status__in=status_list)
        if tag:
            qs = qs.filter(tags__name__icontains=tag)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))
        gte = self.request.query_params.get('updated_gte')
        lte = self.request.query_params.get('updated_lte')
        if gte:
            qs = qs.filter(updated_at__gte=gte)
        if lte:
            qs = qs.filter(updated_at__lte=lte)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                document = Document.objects.create(**serializer.validated_data)
                version_number = document.versions.count() + 1
                DocumentVersion.objects.create(
                    document=document,
                    content=document.content,
                    version_number=version_number,
                    saved_by=document.created_by,
                )
        except IntegrityError:
            return Response({'detail': 'Document could not be created because of a database integrity error.'}, status=status.HTTP_409_CONFLICT)
        document = Document.objects.select_related('workspace', 'created_by').prefetch_related('tags').get(pk=document.pk)
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        try:
            document = Document.objects.get(pk=kwargs['pk'])
        except Document.DoesNotExist:
            return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(document, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                document = serializer.save()
                version_number = document.versions.count() + 1
                DocumentVersion.objects.create(
                    document=document,
                    content=document.content,
                    version_number=version_number,
                    saved_by=document.created_by,
                )
        except IntegrityError:
            return Response({'detail': 'Document update failed and was rolled back.'}, status=status.HTTP_409_CONFLICT)
        document = Document.objects.select_related('workspace', 'created_by').prefetch_related('tags').get(pk=document.pk)
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=['get'], url_path='versions')
    def versions(self, request, pk=None):
        if not Document.objects.filter(pk=pk).exists():
            return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        qs = DocumentVersion.objects.select_related('document', 'saved_by').filter(document_id=pk).order_by('version_number')
        return Response(DocumentVersionSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        document = Document.objects.select_related('workspace', 'created_by').filter(pk=pk).first()
        if not document:
            return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        counts = DocumentVersion.objects.filter(document=document).aggregate(version_count=Count('id', distinct=True))
        comment_count = document.comments.aggregate(total=Count('id', distinct=True))['total'] or 0
        contributor_ids = document.comments.values_list('author_id', flat=True).distinct()
        contributor_count = len([x for x in contributor_ids if x])
        return Response({
            'document_id': str(document.id),
            'version_count': counts['version_count'] or 0,
            'comment_count': comment_count,
            'contributor_count': contributor_count,
        })

    @action(detail=True, methods=['post'], url_path='tags')
    def tags(self, request, pk=None):
        document = Document.objects.prefetch_related('tags').filter(pk=pk).first()
        if not document:
            return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        tag_names = request.data.get('tags', [])
        if not isinstance(tag_names, list) or not tag_names:
            return Response({'detail': 'tags must be a non-empty list of tag names.'}, status=status.HTTP_400_BAD_REQUEST)
        normalized = [str(name).strip() for name in tag_names if str(name).strip()]
        if not normalized:
            return Response({'detail': 'At least one valid tag name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        tags = []
        for name in normalized:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        document.tags.add(*tags)
        return Response({'document_id': str(document.id), 'tags': list(document.tags.values_list('name', flat=True))}, status=status.HTTP_200_OK)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('document', 'author', 'parent')
    serializer_class = CommentSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = Comment.objects.select_related('document', 'author', 'parent').all()
        document_id = self.request.query_params.get('document')
        author_ids = self.request.query_params.get('author')
        if document_id:
            qs = qs.filter(document_id=document_id)
        if author_ids:
            qs = qs.filter(author_id__in=[x.strip() for x in author_ids.split(',') if x.strip()])
        return qs.order_by('created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = serializer.validated_data.get('parent')
        if parent and parent.document_id != serializer.validated_data['document'].id:
            return Response({'detail': 'Parent comment must belong to the same document.'}, status=status.HTTP_400_BAD_REQUEST)
        comment = serializer.save()
        return Response(self.get_serializer(comment).data, status=status.HTTP_201_CREATED)

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get', 'post', 'head', 'options']

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('actor')
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.select_related('actor').all().order_by('-timestamp')
        actor = self.request.query_params.get('actor')
        actor_ids = self.request.query_params.get('actors')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if actor:
            qs = qs.filter(actor_id=actor)
        if actor_ids:
            qs = qs.filter(actor_id__in=[x.strip() for x in actor_ids.split(',') if x.strip()])
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)
        return qs
