from rest_framework import serializers
from .models import User, Workspace, WorkspaceMember, Document, DocumentVersion, Comment, Tag, AuditLog

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at', 'full_name']

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()

    def validate_phone(self, value):
        if not value.isdigit() or not (10 <= len(value) <= 15):
            raise serializers.ValidationError('Phone must contain 10 to 15 digits.')
        return value

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'user', 'user_name', 'user_email', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at', 'workspace', 'user_name', 'user_email']

    def get_user_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'.strip()

    def validate_role(self, value):
        if value not in WorkspaceMember.Role.values:
            raise serializers.ValidationError('Role must be one of: admin, editor, viewer.')
        return value

class WorkspaceSerializer(serializers.ModelSerializer):
    simulate_failure = serializers.BooleanField(write_only=True, required=False, default=False)
    owner_name = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'owner', 'owner_name', 'is_active', 'member_count', 'created_at', 'simulate_failure']
        read_only_fields = ['id', 'created_at', 'owner_name', 'member_count']

    def get_owner_name(self, obj):
        return f'{obj.owner.first_name} {obj.owner.last_name}'.strip()

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('Workspace name cannot be blank.')
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Workspace name must be at least 3 characters.')
        return value.strip()

class DocumentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'workspace', 'created_by', 'created_by_name', 'status', 'tag_names', 'updated_at']
        read_only_fields = ['id', 'updated_at', 'created_by_name', 'tag_names']

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return f'{obj.created_by.first_name} {obj.created_by.last_name}'.strip()

    def get_tag_names(self, obj):
        return list(obj.tags.values_list('name', flat=True))

    def validate(self, attrs):
        title = attrs.get('title', getattr(self.instance, 'title', ''))
        content = attrs.get('content', getattr(self.instance, 'content', ''))
        if not title or not title.strip():
            raise serializers.ValidationError({'title': 'Title is required and cannot be blank.'})
        if content is None:
            raise serializers.ValidationError({'content': 'Content cannot be null.'})
        return attrs

class DocumentVersionSerializer(serializers.ModelSerializer):
    saved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = ['id', 'document', 'content', 'version_number', 'saved_by', 'saved_by_name', 'saved_at']
        read_only_fields = fields

    def get_saved_by_name(self, obj):
        if not obj.saved_by:
            return None
        return f'{obj.saved_by.first_name} {obj.saved_by.last_name}'.strip()

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'document', 'author', 'author_name', 'content', 'parent', 'created_at']
        read_only_fields = ['id', 'created_at', 'author_name']

    def get_author_name(self, obj):
        if not obj.author:
            return None
        return f'{obj.author.first_name} {obj.author.last_name}'.strip()

    def validate(self, attrs):
        parent = attrs.get('parent')
        document = attrs.get('document')
        if parent and document and parent.document_id != document.id:
            raise serializers.ValidationError({'parent': 'Parent comment must belong to the same document.'})
        if not attrs.get('content', '').strip():
            raise serializers.ValidationError({'content': 'Comment content cannot be blank.'})
        return attrs

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'actor', 'actor_name', 'action', 'model_name', 'object_id', 'timestamp']
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        return f'{obj.actor.first_name} {obj.actor.last_name}'.strip()
