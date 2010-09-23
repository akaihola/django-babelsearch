from babelsearch import indexer
from babelsearch.models import IndexEntry, Meaning, Word, ReindexQueue
from babelsearch.preprocess import get_instance_words
from django.conf import settings
import itertools
import os
import stat


DEFAULT_TRIGGER_PATH = '/tmp/babelsearch.reindexer.trigger'

def get_trigger_path():
    return getattr(settings, 'BABELSEARCH_TRIGGER_PATH', DEFAULT_TRIGGER_PATH)


def queue_changes(meanings, spellings):
    for meaning in meanings:
        ReindexQueue.objects.create(type='meaning.pk',
                                    value=meaning.pk)
    for spelling in spellings:
        ReindexQueue.objects.create(type='word.normalized_spelling',
                                    value=spelling)
    file(get_trigger_path(), 'w').close()


def pop_changes():
    meaning_changes = ReindexQueue.objects.filter(
        type='meaning.pk')
    meaning_pks = [change.value for change in meaning_changes]
    meaning_changes.delete()

    spelling_changes = ReindexQueue.objects.filter(
        type='word.normalized_spelling')
    spellings = [change.value for change in spelling_changes]
    spelling_changes.delete()

    return meaning_pks, spellings


def get_batches_for(model, size=100):
    instances = iter(model.objects.order_by('pk'))
    while True:
        batch = list(itertools.islice(instances, size))
        if not batch:
            break
        yield batch


def get_changed_instances(instances, changed_instance_pks, changed_spellings):
    """Yields all potentially changed instances

    Yields those instances:

    * whose primary key is in ``changed_instance_pks``

    * whose indexable fields contain any of the strings in ``changed_spellings``
    """
    for instance in instances:
        if instance.pk in changed_instance_pks:
            yield instance
            continue
        for word in get_instance_words(instance):
            for spelling in changed_spellings:
                if spelling in word:
                    yield instance

            
def reindex_model_for_meanings(
    model, changed_meaning_pks, changed_spellings, callback=None):
    """Re-indexes potentially changed instances of a model

    Arguments:

    * ``changed_meaning_pks``: list of primary keys for Meaning
      instances known to have changed

    * ``changed_spellings``: list of added, removed and
      meaning-changed normalized spellings
    """
    changed_instance_pks = (
        model.objects
        .filter(index_entries__meaning__in=changed_meaning_pks)
        .values_list('pk', flat=True))
    for batch in get_batches_for(model, size=100):
        for instance in get_changed_instances(
            batch, changed_instance_pks, changed_spellings):

            if callback:
                callback(unicode(instance))
            IndexEntry.objects.index_instance(instance)


def reindex_for_meanings(changed_meaning_pks, changed_spellings, callback=None):
    for model, fields in indexer.registry.items():
        reindex_model_for_meanings(
            model, changed_meaning_pks, changed_spellings, callback=callback)


def reindex_for_changes(callback=None):
    changed_meaning_pks, changed_spellings = pop_changes()
    if changed_meaning_pks or changed_spellings:
        callback('Changed meanings: %s' % changed_meaning_pks)
        callback('Changed spellings: %s' % changed_spellings)
        reindex_for_meanings(changed_meaning_pks, changed_spellings, callback=callback)
