from django.db import models
from django.contrib.contenttypes import generic

from babelsearch import indexer
from babelsearch.models import IndexEntry

class Author(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __unicode__(self):
        return self.name

class Sentence(models.Model):
    authors = models.ManyToManyField(Author)
    text = models.CharField(max_length=300)
    index_entries = generic.GenericRelation(IndexEntry)

    def __unicode__(self):
        authors = self.authors.all() or ['?']
        return '[%s: %s]' % (
            '; '.join(unicode(a) for a in authors),
            self.text)

indexer.register(Sentence, ('authors__name', 'text',))
#indexer.register(Sentence, ('text',))
