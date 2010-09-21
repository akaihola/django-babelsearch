from django.db import models, connection
from django.db.models import F
from django.db.models.signals import post_syncdb
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
import operator

from babelsearch.datastruct import SetList, PrefixCache
from babelsearch.preprocess import get_words, get_instance_words


def unique_substrings(s):
    found = set()
    for i in range(len(s)):
        for j in range(i+1, len(s)+1):
            substring = s[i:j]
            if substring not in found:
                yield substring
                found.add(substring)


def divisions(s, vocabulary, max_parts=3, min_lengths=(1, 3)):
    """Generate complete divisions of a string into words in vocabulary

    * ``max_parts`` is the maximum number of parts to divide into
    * ``min_lengths`` is the minimum part length at different levels
      of recursion

    With the value of ``min_lengths=(1, 3)``, only non-blank (length
    >= 1) original strings are yielded, and if the string is divided,
    each part must have at least three characters.
    """
    for i in range(1, len(s)+1):
        substring = s[:i]
        if len(substring) >= min_lengths[0] and substring in vocabulary:
            if i == len(s):
                yield substring,
            else:
                # when recursing, pop first item from min_lengths
                # unless it only has one
                next_min_lengths = min_lengths[min(1, len(min_lengths)-1):]
                for subsubstrings in divisions(s[i:], vocabulary,
                                               max_parts=max_parts,
                                               min_lengths=next_min_lengths):
                    if len(subsubstrings) < max_parts:
                        yield (substring,) + subsubstrings


def sort_divisions(divs):
    # decorate
    decdivs = [(len(div), -min(len(substring) for substring in div), div)
               for div in divs]
    decdivs.sort()
    # undecorate
    return [item[2] for item in decdivs]


def sorted_divisions(s, vocabulary, max_parts=3, min_lengths=(1, 3)):
    return sort_divisions(
        divisions(s, vocabulary,
                  max_parts=max_parts, min_lengths=min_lengths))


class Word(models.Model):
    normalized_spelling = models.CharField(max_length=100)
    language = models.CharField(max_length=5, null=True)
    frequency = models.IntegerField(default=0)
    indexable = models.BooleanField(default=True)

    @classmethod
    def _get_cache(cls):
        if not hasattr(cls, '_cache'):
            cls._cache = PrefixCache(cls, 'normalized_spelling')
        return cls._cache

    def save(self, **kwargs):
        super(Word, self).save(**kwargs)
        Word._get_cache().add(self.normalized_spelling)

    def delete(self):
        super(Word, self).delete()
        Word._get_cache().discard(self.normalized_spelling)

    class Meta:
        unique_together = ('normalized_spelling', 'language'),
        ordering = 'language', 'normalized_spelling',

    def __unicode__(self):
        return '%s:%s/%d' % (
            self.language, repr(self.normalized_spelling)[2:-1], self.frequency)

class MeaningManager(models.Manager):

    def create(self, *args, **kwargs):
        words = kwargs.pop('words', ())
        meaning = super(MeaningManager, self).create(*args, **kwargs)
        meaning.add_words(words)
        return meaning

    def join(self, *meanings):
        """
        Copies all words to the first meaning from all the rest of the
        meanings.  Deletes the rest of the meanings.

        TODO: improve performance
        """
        for meaning in meanings[1:]:
            for word in meaning.words.all():
                meanings[0].words.add(word)
            for indexentry in meaning.index_entries.all():
                indexentry.meaning = meanings[0]
                indexentry.save()
            meaning.delete()
        return meanings[0]

    def split(self, meaning, *part_meanings):
        """
        Copies all index entries to part_meanings from the first
        meaning.  Deletes the first meaning.  Assumes words are
        already set up correctly.

        TODO: improve performance
        """
        for indexentry in meaning.index_entries.all():
            indexentry.meaning = part_meanings[0]
            indexentry.save()
            for part_meaning in part_meanings[1:]:
                indexentry.id = None
                indexentry.meaning = part_meaning
                indexentry.save()
        meaning.delete()
        return part_meanings

    def lookup_exact(self, normalized_spelling):
        """
        Returns a queryset with all the meanings which have the given
        normalized spelling in at least one language.
        """
        if Word._get_cache().contains(normalized_spelling):
            return self.filter(words__normalized_spelling=normalized_spelling)
        else:
            return self.none()

    def lookup_splitting(self, word,
                         create_missing=False, found_words=None):
        """
        Tries to find meanings for the given word in the dictionary,
        possibly splitting the word up into multiple pieces and
        assuming it's a compound word.  Prefers a split with as few
        and long parts as possible.

        If no matches are found and `create_missing == True`, the word
        is added to the dictionary and attached to a new meaning.

        Returns a 2-tuple of
         * a queryset of meanings
         * a list of matched words (as strings)

        The list of words is either the original word or the parts it
        was split up into.
        """
        all_substrings = unique_substrings(word)
        found_words = Word.objects.filter(
            normalized_spelling__in=all_substrings, indexable=True)
        found_spellings = found_words.values_list(
            'normalized_spelling', flat=True)
        possible_divisions = sorted_divisions(word, found_spellings)

        if possible_divisions:
            found_words = possible_divisions[0]
            meanings_for_division = (self.lookup_exact(w)
                                     for w in found_words)
            meanings = reduce(operator.or_, meanings_for_division).distinct()

        else:  # no divisions found
            if create_missing:  # add word to index and use it as the match
                new_meaning = self.create(words=((None, word),))
                found_words = word,
                meanings = self.filter(pk=new_meaning.pk).distinct()
            else:  #  don't add word to index, no match
                meanings = self.none()
                found_words = []

        return meanings, found_words

    def lookup(self, normalized_spellings, create_missing=False):
        """
        Returns a 2-tuple of
         * a queryset of all meanings associated with any of
          `normalized_spellings`.
         * a set of all found words

        If `create_missing` is `True`, creates words and meanings for
        words not found.  In this case the set of found words contains
        all searched words.

        This is similar to `lookup_ordered` but only fires one query
        since matches don't have to be partitioned by word order.
        """
        Word._get_cache().seed(normalized_spellings)
        result = self.none()
        found_words = set()
        for word in set(normalized_spellings):
            meanings, words = self.lookup_splitting(
                word, create_missing=create_missing)
            found_words.update(words)
            result |= meanings
        return result, found_words

    def lookup_ordered(self, normalized_spellings, create_missing=False):
        """
        Returns a 2-tuple of
         * a SetList which contains, for each word in
          `normalized_spellings`, a set of all meanings associated
           with the word
         * a set of all found words

        If `create_missing` is `True`, creates words and meanings for
        words not found.  In this case the set of found words contains
        all searched words.
        """
        Word._get_cache().seed(normalized_spellings)
        result = SetList()
        found_words = set()
        cache = {}
        for word in normalized_spellings:
            if word not in cache:
                meanings, words = self.lookup_splitting(
                    word, create_missing=create_missing)
                cache[word] = list(meanings)
                found_words.update(words)
            result.append(cache[word])
        return result, found_words

    def lookup_sentence(self, sentence):
        return self.lookup_ordered(get_words(sentence))

class Meaning(models.Model):
    words = models.ManyToManyField(Word)

    objects = MeaningManager()

    def __unicode__(self):
        words = self.words.order_by('language', 'normalized_spelling')
        return u'%d: %s' % (
            self.pk,
            u','.join(u'%s:%s' % (w.language, repr(w.normalized_spelling)[2:-1])
                      for w in words))

    def add_words(self, words):
        for word in words:
            w = None
            if Word._get_cache().contains(word[1]):
                try:
                    w = Word.objects.get(
                        language=word[0], normalized_spelling=word[1])
                except Word.DoesNotExist:
                    pass
            if w is None:
                w = Word.objects.create(
                    language=word[0], normalized_spelling=word[1])
            self.words.add(w)

class IndexManager(models.Manager):

    def index_instance(self, instance):
        self.delete_for_instance(instance)
        self.create_for_instance(instance)

    def delete_for_instance(self, instance):
        model = instance.__class__
        ctype = ContentType.objects.get_for_model(model)
        (Word.objects
         .filter(meaning__index_entries__content_type=ctype,
                 meaning__index_entries__object_id=instance.pk)
         .update(frequency=F('frequency')-1))
        self.filter(content_type=ctype, object_id=instance.pk).delete()

    def create_for_instance(self, instance):
        """
        Creates index entries for the given instance.  An index entry
        is created for every meaning corresponding to a word in fields
        of the instance.  Dummy meanings are created for words not yet
        in the vocabulary.  Frequencies of words found are
        incremented.
        """
        words = get_instance_words(instance)
        ordered_meanings, found_words = Meaning.objects.lookup_ordered(
            words, create_missing=True)
        for order, meanings in enumerate(ordered_meanings):
            for meaning in meanings:
                self.create(content_object=instance,
                            order=order+1,
                            meaning=meaning)
        word_instances = Word.objects.filter(normalized_spelling__in=found_words)
        word_instances.update(frequency=F('frequency')+1)


class IndexEntry(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    order = models.PositiveIntegerField()
    meaning = models.ForeignKey(Meaning, related_name='index_entries')

    objects = IndexManager()

    def __unicode__(self):
        return '%s[%d] = %s' % (
            unicode(self.content_object), self.order, unicode(self.meaning))

    class Meta:
        unique_together = ('content_type', 'object_id', 'order', 'meaning'),
        ordering = 'content_type', 'object_id', 'order',

def get_index_info_for_meanings(model, meanings):
    """
    Returns a sorted list of 3-tuples for each index entry matching
    the given model and set of meanings.  The elements of the 3-tuple
    are:
     * the primary key of the model instance
     * the order of the meaning in the instance's indexed text
     * the primary key of the meaning
    """
    ctype = ContentType.objects.get_for_model(model)
    return (
        IndexEntry.objects.filter(meaning__in=meanings, content_type=ctype)
        .values('object_id', 'order', 'meaning')
        .order_by('object_id', 'order')
        .distinct())

def calculate_score(matching_meanings, unique_search_meanings):
    """
          matching unique meanings btw model inst & search str
    100 * ----------------------------------------------------
          total number of unique meanings in the search string
    """
    return 100 * len(matching_meanings.flat) / unique_search_meanings

def get_scored_matches(model, meaning_search):
    """
    Returns a relevance-sorted list of all instances of the given
    model which match any of the given meanings in the index.

    `meaning_search` is a list of querysets of `Meaning`s, one for
    every word in the search terms

    Let's assume:
     * meaning_search: [[Bach], [Complete], [Oeuvre,ToFunction]]
     * obj1: 'Works of Art'
     * obj2: 'Schubert: Oeuvres completes'
     * obj3: 'Bach: Complete Works'
    `instances` might ends up like this:
    {obj1_id: [[Oeuvre], [], []],
     obj2_id: [[], [Oeuvre], [Complete]],
     obj3_id: [[Bach], [Complete], [Oeuvre,ToFunction]]}
    """
    rows = get_index_info_for_meanings(model, meaning_search.flat)
    object_ids = set(row['object_id'] for row in rows)
    meaning_dict = dict((m.pk, m) for m in meaning_search.flat)
    instance_matches = dict((pk, SetList()) for pk in object_ids)
    # rows: [{'object_id': <int>, 'order': <int>, 'meaning': <Meaning>}, ...]
    # object_ids: set([object_id, ...])
    # meaning_dict: {object_id: Meaning, ...}
    for row in rows: # row = (object_id, order, meaning_id)
        meanings = instance_matches[row['object_id']] # SetList
        position = meanings[row['order']] # SetWrapper
        meaning = meaning_dict[row['meaning']] # Meaning
        position.add(meaning)
    term_count = len(meaning_search.flat)
    # `term_count` = number of word meanings in search string,
    # including multiple meanings for one word.
    scores = ( (calculate_score(matches, term_count), pk)
               for (pk, matches) in instance_matches.iteritems() )
    sorted_scores = sorted(scores, reverse=True)
    return sorted_scores

def get_scored_matches_for_sentence(model, sentence, offset=0, limit=50):
    """
    Analyses the given sentence, searches all instances of the given
    model which match at least one word meaning in the sentence and
    returns a list of instances in descending order of relevance.
    Limits the list to the first 50 matches by default.
    """
    meanings, words = Meaning.objects.lookup_sentence(sentence)
    matches = get_scored_matches(model, meanings)[offset:offset+limit]
    instance_ids = [pk for (score, pk) in matches]
    instance_dict = model.objects.in_bulk(instance_ids)
    return [{'instance': instance_dict[pk], 'score': score}
            for (score, pk) in matches]

def create_babelsearch_indexes_postgresql(**kwargs):
    name = 'babelsearch_word_spelling'
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM pg_indexes WHERE indexname = %s', (name,))
    if len(cursor.fetchall()) == 0:
        cursor.execute('CREATE INDEX babelsearch_word_spelling '
                       'ON babelsearch_word (normalized_spelling);')
    cursor.close()

if settings.DATABASE_ENGINE.startswith('postgresql'):
    post_syncdb.connect(create_babelsearch_indexes_postgresql)
