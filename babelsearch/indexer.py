from django.db.models.signals import post_save

registry = {}

def index_instance(instance, created, raw, **kwargs):
    """
    Callback for the `post_save` signal.  Creates index entries for
    words which appear in the instance.  Only examines fields
    registered for the model of the instance.
    """
    if not raw:
        from babelsearch.models import IndexEntry
        if not created:
            IndexEntry.objects.delete_for_instance(instance)
        IndexEntry.objects.create_for_instance(instance)

def register(model, fields):
    """
    Registers a model for automatic indexing.  Only indexes fields
    mentioned in `fields`.
    """
    registry[model] = fields
    post_save.connect(index_instance, sender=model)
