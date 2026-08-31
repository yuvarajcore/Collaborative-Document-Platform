from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document, AuditLog

@receiver(post_save, sender=Document)
def document_audit_log(sender, instance, created, **kwargs):
    AuditLog.objects.create(
        actor=instance.created_by,
        action='created' if (created or instance._state.adding) else 'updated',
        model_name='Document',
        object_id=str(instance.id),
    )
