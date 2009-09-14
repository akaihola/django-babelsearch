from django.db.models.signals import pre_save, post_save, pre_delete

registry = {}

def unindex_old_instance(sender, instance, raw, **kwargs):
    """
    Callback for the `pre_save` signal.  Removes index entries for
    words which appear in the old version of the instance.  Only
    examines fields registered for the model of the instance.  Also
    decrements frequencies for the spellings of the words.
    """
    if not raw and instance.pk is not None:
        from babelsearch.models import IndexEntry
        try:
            old_instance = instance.objects.get(pk=instance.pk)
            IndexEntry.objects.delete_for_instance(old_instance)
        except sender.DoesNotExist:
            pass

def index_instance(instance, created, raw, **kwargs):
    """
    Callback for the `post_save` signal.  Creates index entries for
    words which appear in the instance.  Only examines fields
    registered for the model of the instance.  Also increments
    frequencies for the spellings of the words.
    """
    if not raw:
        from babelsearch.models import IndexEntry
        IndexEntry.objects.create_for_instance(instance)

def unindex_instance(instance, **kwargs):
    """
    Callback for the `pre_delete` signal.  Removes index entries for
    words which appear in the instance.  Also decrements frequencies
    for the spellings of the words.
    """
    from babelsearch.models import IndexEntry
    IndexEntry.objects.delete_for_instance(instance)

def register(model, fields):
    """
    Registers a model for automatic indexing.  Only indexes fields
    mentioned in `fields`.
    """
    registry[model] = fields
    pre_save.connect(unindex_old_instance, sender=model)
    post_save.connect(index_instance, sender=model)
    pre_delete.connect(unindex_instance, sender=model)
