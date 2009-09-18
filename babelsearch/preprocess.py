import re
from unicodedata import combining, normalize

from django.db import models

from babelsearch.indexer import registry

replace_numbers = re.compile(r'(\d+)').sub
split_words = re.compile(r"\w+(?:'\w+)?", re.U).findall

def tokenize(s):
    """
    Returns a list of all words and figures in a string.
    """
    return split_words(replace_numbers(r' \1 ', s))

def lower_without_diacritics(s):
    """
    Removes diacritical marks from all symbols in a string and
    converts it to lower case.
    """
    return filter(lambda u: not combining(u), normalize('NFKD', s)).lower()

def get_words(s):
    """
    Finds all words and figures in string `s`, strips diacritics from
    them, lowercases them and returns them as a list.
    """
    return tokenize(lower_without_diacritics(s))

def resolve_field_value(instances, path):
    """
    Walks object relations and finds all values for the given
    attribute path.  Returns the values as a list.

    Let's assume `instances` is a list of authors, and there's a
    many-to-many relation between authors and books.  If the path is
    `['books', 'publisher', 'name']`, this function would return a
    list of publisher names of all books by all the given authors.
    """
    if not path:
        return instances
    values = []
    for instance in instances:
        attr = getattr(instance, path[0])
        if isinstance(attr, models.Manager):
            value = resolve_field_value(attr.all(), path[1:])
        elif isinstance(attr, models.Model):
            value = resolve_field_value(attr, path[1:])
        else:
            value = resolve_field_value([attr], path[1:])
        values.extend(value)
    return values

def get_instance_words(instance):
    """
    Returns a list of normalized words and figures in a registered
    model instance.  The fields whose contents are to be considered
    are specified when registering the model.
    """
    values = []
    for fieldname in registry[instance.__class__]:
        values.extend(resolve_field_value(
                [instance], fieldname.split('__')))
    return get_words(u' '.join(values))
