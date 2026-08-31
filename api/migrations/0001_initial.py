import uuid
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('email', models.CharField(max_length=254, unique=True)),
                ('phone', models.CharField(max_length=15, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Workspace',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_workspaces', to='api.user')),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('admin','Admin'),('editor','Editor'),('viewer','Viewer')], max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspace_memberships', to='api.user')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='api.workspace')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('workspace','user'), name='unique_workspace_member')]},
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('status', models.CharField(choices=[('draft','Draft'),('published','Published'),('archived','Archived')], max_length=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents_created', to='api.user')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='api.workspace')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='comments', to='api.user')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='api.document')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='api.comment')),
            ],
        ),
        migrations.CreateModel(
            name='DocumentVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('version_number', models.PositiveIntegerField()),
                ('saved_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='api.document')),
                ('saved_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_versions_saved', to='api.user')),
            ],
            options={'ordering':['version_number'],'constraints':[models.UniqueConstraint(fields=('document','version_number'), name='unique_document_version_number')]},
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=50)),
                ('model_name', models.CharField(max_length=100)),
                ('object_id', models.CharField(max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='api.user')),
            ],
        ),
        migrations.AddField(
            model_name='tag', name='documents',
            field=models.ManyToManyField(blank=True, related_name='tags', to='api.document'),
        ),
    ]
