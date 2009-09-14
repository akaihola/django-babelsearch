import re
from unicodedata import combining, normalize

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from babelsearch.indexer import registry

class Word(models.Model):
    normalized_spelling = models.CharField(max_length=100)
    language = models.CharField(max_length=5)

    # objects = WordManager()

    class Meta:
        unique_together = ('normalized_spelling', 'language'),

    def __unicode__(self):
        return self.normalized_spelling

    def __repr__(self):
        return '<Word: %s (%s)>' % (self.normalized_spelling, self.language)

class MeaningManager(models.Manager):

    def create(self, *args, **kwargs):
        words = kwargs.pop('words', {})
        meaning = super(MeaningManager, self).create(*args, **kwargs)
        meaning.add_words(words)
        return meaning

    def lookup_exact(self, normalized_spelling):
        return self.filter(words__normalized_spelling=normalized_spelling)

    def lookup_splitting(self, prefix, suffix=u''):
        if not prefix:
            return self.none()
        prefixes = self.lookup_exact(prefix)
        if prefixes:
            if not suffix:
                return prefixes.distinct()
            suffixes = self.lookup_exact(suffix)
            if suffixes:
                return (prefixes | suffixes).distinct()
        return self.lookup_splitting(prefix[:-1], prefix[-1] + suffix)

    def lookup(self, normalized_spellings):
        result = self.none()
        for word in normalized_spellings:
            result |= self.lookup_splitting(word)
        return result

    _tokenize = re.compile(r'[^\w]', re.U).split

    @staticmethod
    def _remove_diacritics(s):
        return filter(lambda u: not combining(u), normalize('NFKD', s))

    def lookup_sentence(self, sentence):
        return self.lookup(self._tokenize(self._remove_diacritics(sentence)))

class Meaning(models.Model):
    words = models.ManyToManyField(Word)

    objects = MeaningManager()

    def __unicode__(self):
        words = self.words.order_by('language', 'normalized_spelling')
        return '%d: %s' % (
            self.pk,
            ','.join('%s:%s' % (w.language, w.normalized_spelling)
                     for w in words))

    def add_words(self, words):
        for word in words:
            w, created = Word.objects.get_or_create(language=word[0],
                                                    normalized_spelling=word[1])
            self.words.add(w)

class IndexManager(models.Manager):

    def index_instance(self, instance):
        self.delete_for_instance(instance)
        return self.create_for_instance(instance)

    def delete_for_instance(self, instance):
        model = instance.__class__
        ctype = ContentType.objects.get_for_model(model)
        self.filter(content_type=ctype, object_id=instance.pk).delete()

    def create_for_instance(self, instance):
        result = []
        for fieldname in registry[instance.__class__]:
            value = getattr(instance, fieldname)
            result.append('meanings for %s %r in model %r' % (
                    fieldname, value, instance.__class__.__name__))
            meanings = Meaning.objects.lookup_sentence(value)
            for order, meaning in enumerate(meanings):
                self.create(content_object=instance,
                            order=order+1,
                            meaning=meaning)
                result.append(meaning)
        return result

    def search(self, sentence):
        search_meanings = Meaning.objects.lookup_sentence(sentence)
        matches = self.filter(meaning__in=search_meanings)
        return matches

class IndexEntry(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    order = models.PositiveIntegerField()
    meaning = models.ForeignKey(Meaning)

    objects = IndexManager()

    def __unicode__(self):
        return '%s[%d] = %s' % (
            unicode(self.content_object), self.order, unicode(self.meaning))

    class Meta:
        unique_together = ('content_type', 'object_id', 'order', 'meaning'),
