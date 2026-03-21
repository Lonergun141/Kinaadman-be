from ninja import ModelSchema
from core.models import AuditLog

class AuditLogSchema(ModelSchema):
    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'entity_type', 'entity_id', 'metadata', 'created_at']
