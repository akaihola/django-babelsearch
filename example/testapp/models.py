from django.db import models
from django.contrib.contenttypes import generic

from babelsearch import indexer
from babelsearch.models import IndexEntry

class Sentence(models.Model):
    text = models.CharField(max_length=300)
    index_entries = generic.GenericRelation(IndexEntry)

    def __unicode__(self):
        return repr(self.text)

indexer.register(Sentence, ('text',))
