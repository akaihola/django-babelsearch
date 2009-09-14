import re
from unicodedata import combining, normalize

from django.db import models
from django.db.models import F
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from babelsearch.indexer import registry

class Word(models.Model):
    normalized_spelling = models.CharField(max_length=100)
    language = models.CharField(max_length=5, null=True)
    frequency = models.IntegerField(default=0)

    # objects = WordManager()

    class Meta:
        unique_together = ('normalized_spelling', 'language'),

    def __unicode__(self):
        return self.normalized_spelling

    def __repr__(self):
        return '<Word: %s (%s/%d)>' % (
            self.normalized_spelling, self.language, self.frequency)

class MeaningManager(models.Manager):

    def create(self, *args, **kwargs):
        words = kwargs.pop('words', {})
        meaning = super(MeaningManager, self).create(*args, **kwargs)
        meaning.add_words(words)
        return meaning

    def lookup_exact(self, normalized_spelling):
        return self.filter(words__normalized_spelling=normalized_spelling)

    def lookup_splitting(self,
                         prefix, suffix=u'',
                         create_missing=False, found_words=None):
        if found_words is None:
            found_words = []
        if not prefix:
            # no matches were found, suffix = original search term
            if create_missing:
                new_meaning = self.create(words=((None, suffix),))
                found_words.append(suffix)
                meanings = self.filter(pk=new_meaning.pk).distinct()
            else:
                meanings = self.none()
        else:
            prefixes = self.lookup_exact(prefix)
            if prefixes:
                if not suffix:
                    # original search term found
                    found_words.append(prefix)
                    meanings = prefixes.distinct()
                else:
                    suffixes, w = self.lookup_splitting(
                        suffix, found_words=found_words)
                    if suffixes:
                        # compound word match found
                        found_words.append(prefix)
                        meanings = (prefixes.distinct() | suffixes)
                    else:
                        meanings = self.none()
            else:
                # no matches for this division, divide one char earlier
                meanings, sub_words = self.lookup_splitting(
                    prefix[:-1], prefix[-1] + suffix,
                    create_missing=create_missing, found_words=found_words)
        return meanings, found_words

    def lookup(self, normalized_spellings, create_missing=False):
        result = self.none()
        found_words = []
        for word in normalized_spellings:
            meanings, words = self.lookup_splitting(
                word, create_missing=create_missing)
            result |= meanings
            found_words.extend(words)
        return result, found_words

    _tokenize = re.compile(r'[^\w]', re.U).split

    @staticmethod
    def _remove_diacritics(s):
        return filter(lambda u: not combining(u), normalize('NFKD', s))

    @staticmethod
    def _get_words(s):
        return set(
            MeaningManager._tokenize(MeaningManager._remove_diacritics(s)))

    def lookup_sentence(self, sentence):
        return self.lookup(self._get_words(sentence))

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
        self.create_for_instance(instance)

    @staticmethod
    def _get_instance_words(instance):
        fieldnames = registry[instance.__class__]
        text = u' '.join(getattr(instance, fieldname)
                         for fieldname in fieldnames)
        return Meaning.objects._get_words(text)

    def delete_for_instance(self, instance):
        model = instance.__class__
        ctype = ContentType.objects.get_for_model(model)
        self.filter(content_type=ctype, object_id=instance.pk).delete()
        words = self._get_instance_words(instance)
        meanings, found_words = Meaning.objects.lookup(words)
        Word.objects.filter(normalized_spelling__in=found_words).update(
            frequency=F('frequency')-1)

    def create_for_instance(self, instance):
        """
        Creates index entries for the given instance.  An index entry
        is created for every meaning corresponding to a word in fields
        of the instance.  Dummy meanings are created for words not yet
        in the vocabulary.  Frequencies of words found are
        incremented.
        """
        words = self._get_instance_words(instance)
        meanings, found_words = Meaning.objects.lookup(
            words, create_missing=True)
        for order, meaning in enumerate(meanings):
            self.create(content_object=instance,
                        order=order+1,
                        meaning=meaning)
        Word.objects.filter(normalized_spelling__in=found_words).update(
            frequency=F('frequency')+1)

    def search(self, sentence):
        search_meanings, words = Meaning.objects.lookup_sentence(sentence)
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
