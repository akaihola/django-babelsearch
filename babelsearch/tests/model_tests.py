# -*- coding: utf-8 -*-

from django.test import TestCase
from pprint import pformat

from django.db import IntegrityError
from django.db.models import F

from babelsearch.models import Meaning, Word, IndexEntry
from babelsearch.indexer import registry
from babelsearch.preprocess import tokenize, lower_without_diacritics, get_words
from babelsearch.tests.testapp.models import Author, Sentence


def tuplify(seq):
    if isinstance(seq, (list, tuple)):
        return tuple(tuplify(item) for item in seq)
    return seq


def listify(seq):
    if isinstance(seq, (list, tuple, set)):
        return sorted(listify(item) for item in seq)
    return seq


def setify(seq):
    if isinstance(seq, (list, tuple)):
        return set(tuplify(item) for item in seq)
    return seq
        

def format_word(word):
    return '%s:%s' % (str(word.language or '?'), str(word.normalized_spelling))


def assert_meaning(meaning, *expected_words):
    actual_words = tuple(format_word(w) for w in meaning.words.all())
    assert actual_words == expected_words, 'Expected: %s\nGot: %s' % (
        pformat(expected_words), pformat(actual_words))


def dump_meanings():
    return [[format_word(w) for w in m.words.all()]
            for m in Meaning.objects.all()]


def assert_meanings(*expected_meanings):
    expected = listify(expected_meanings)
    actual_meanings = listify(dump_meanings())
    assert actual_meanings == expected, 'Expected: %s\nGot: %s' % (
        pformat(expected), pformat(actual_meanings))


def assert_index(instance, *expected_meanings):
    actual_meanings = tuple(
        [i.order] + [format_word(w) for w in i.meaning.words.all()]
        for i in instance.index_entries.all())
    assert actual_meanings == expected_meanings, 'Expected: %s\nGot: %s' % (
        expected_meanings, listify(actual_meanings))


class MeaningPreProcessTests(TestCase):

    def test_01_tokenize(self):
        self.assertEqual(tokenize('a b c'), ['a', 'b', 'c'])

    def test_02_tokenize_unstripped(self):
        self.assertEqual(tokenize(' a b c '), ['a', 'b', 'c'])

    def test_03_tokenize_unicode(self):
        self.assertEqual(
            tokenize(u'Saint-Saëns Martinů tästä'),
            [u'Saint', u'Saëns', u'Martinů', u'tästä'])

    def test_04_tokenize_digits(self):
        self.assertEqual(tokenize(u' KV 457 BWV3 '),
                         [u'KV', u'457', u'BWV', u'3'])

    def test_05_tokenize_apostrophes(self):
        self.assertEqual(tokenize(u" 'wow' l'automne Bob's "),
                         [u'wow', u"l'automne", u"Bob's"])

    def test_06_normalize(self):
        self.assertEqual(lower_without_diacritics(u'Saint-Saëns Martinů'),
                         u'saint-saens martinu')

    def test_07_get_words(self):
        self.assertEqual(
            get_words(
                u" Saint-Saëns: 'Hommage' à Martinů's dad SS34 "),
            [u'saint', u'saens', u'hommage', u'a', u"martinu's", u'dad', u'ss', u'34'])

class MeaningCreationTests(TestCase):

    def test_01_add_empty_meaning(self):
        m = Meaning.objects.create()
        self.assertEqual(list(m.words.all()), [])

    def test_02_add_words_to_meaning(self):
        m = Meaning.objects.create()
        m.words.create(normalized_spelling='home', language='fi')
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: fi:home/0>'])
        m.words.create(normalized_spelling='mold', language='en')
        assert_meaning(m, 'en:mold', 'fi:home')

    def test_03_create_meaning_with_words(self):
        m = Meaning.objects.create(
            words=[('en', 'home'), ('fi', 'koti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: en:home/0>', '<Word: fi:koti/0>'])
        self.assertEqual(Word.objects.count(), 2)

    def test_04_create_duplicate_word(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: en:mold/0>', '<Word: fi:muotti/0>'])
        self.assertEqual(Word.objects.count(), 2)
        self.assertEqual(repr(Word.objects.all()[1]), '<Word: fi:muotti/0>')

    def test_05_cannot_add_duplicate_word_with_create(self):
        m = Meaning.objects.create(words=[('en', 'mold'), ('fi', 'vuoka')])
        self.assertRaises(IntegrityError, m.words.create,
                          language='en', normalized_spelling='mold')
        self.assertEqual(repr(m), '<Meaning: 1: en:mold,fi:vuoka>')

    def test_06_add_duplicate_word_with_get_or_create(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: en:mold/0>', '<Word: fi:muotti/0>'])
        mold, created = m.words.get_or_create(
            language='en', normalized_spelling='mold')
        self.assertEqual(mold, m.words.get(normalized_spelling='mold'))
        self.assertFalse(created)

    def test_07_add_duplicate_word_with_model_method(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        m.add_words([('en', 'mold')])

class MeaningHelpers(object):
    def assertMeanings(self, queryset, *expected_meanings):
        """
        Given two sequences of meaning instances, asserts that they
        are identical.  Sorts the first sequence by id and expects the
        second one to be pre-sorted.
        """
        meanings = tuple(sorted(queryset, key=lambda m: m.pk))
        self.assertEqual(meanings, expected_meanings)

    def assertMeaningTree(self, got_tree, *expected_tree):
        """
        Given two sequences of sequences of meanings, asserts that
        they are equal.
        """
        self.assertEqual(len(got_tree), len(expected_tree))
        for meanings, expected_meanings in zip(got_tree, expected_tree):
            self.assertMeanings(meanings, *expected_meanings)

    def get_meaning_changes(self):
        new_meanings = dump_meanings()
        try:
            old_meanings = self.previous_meanings_dump
        except AttributeError:
            actual_removed = ()
            actual_added = new_meanings
        else:
            actual_removed = setify(old_meanings).difference(
                setify(new_meanings))
            actual_added = setify(new_meanings).difference(
                setify(old_meanings))
        self.previous_meanings_dump = new_meanings
        return actual_removed, actual_added
        
    def assert_meaning_changes(self, removed=(), added=()):
        actual_removed, actual_added = self.get_meaning_changes()
        assert (not setify(removed).symmetric_difference(setify(actual_removed)) and
                not setify(added).symmetric_difference(setify(actual_added))), (
            'Expected:\nremoved=%r,\nadded=%r\nGot:\nremoved=%r,\nadded=%r' % (
                listify(removed), listify(added),
                listify(actual_removed), listify(actual_added)))
        
    def create_meaning(self, *words):
        return Meaning.objects.create(
            words=[item.split(':') for item in words])

    def lookup_meanings(self, word):
        return Meaning.objects.lookup_exact(word)

    def lookup_one_meaning(self, word):
        return self.lookup_meanings(word)[0]

    def new_sentence(self, text):
        return Sentence.objects.create(text=text)


class MeaningAnalysisTests(TestCase, MeaningHelpers):

    def setUp(self):
        c = self.create_meaning
        self.mold_fungus = c('en:mold', 'fi:home')
        self.mold_food = c('en:mold', 'fi:vuoka')
        self.mold_manufacturing = c('en:mold', 'fi:muotti')
        self.home = c('en:home', 'fi:koti')
        self.piano = c('en:piano', 'fi:piano', 'de:klavier')
        self.concerto = c('en:concerto', 'fi:konsertto', 'de:konzert')

    def test_01_lookup_unambiguous(self):
        self.assertMeanings(Meaning.objects.lookup_exact('vuoka'),
                            self.mold_food)

    def test_02_lookup_ambiguous(self):
        self.assertMeanings(
            Meaning.objects.lookup_exact('mold'),
            self.mold_fungus, self.mold_food, self.mold_manufacturing)

    def test_03_lookup_language_ambiguous(self):
        self.assertMeanings(Meaning.objects.lookup_exact('home'),
                            self.mold_fungus, self.home)

    def test_04_lookup_unknown(self):
        self.assertFalse(Meaning.objects.lookup_exact('flabbergasted'))

    def test_05_lookup_compound_debug1(self):
        meanings, words = Meaning.objects.lookup_splitting(u'konsertto')
        self.assertMeanings(meanings, self.concerto)
        self.assertEqual(words, (u'konsertto',))

    def test_06_lookup_compound(self):
        meanings, words = Meaning.objects.lookup_splitting('pianokonsertto')
        self.assertMeanings(meanings, self.piano, self.concerto)
        self.assertEqual(words, (u'piano', u'konsertto'))

    def test_07_lookup_unknown_compound(self):
        meanings, words = Meaning.objects.lookup_splitting('pianokonsertt')
        self.assertMeanings(meanings)
        self.assertEqual(words, [])

    def test_08_lookup_create_unknown(self):
        meanings, words = Meaning.objects.lookup_splitting(
            'fuge', create_missing=True)
        assert_meanings(['en:mold', 'fi:home'],
                        ['en:mold', 'fi:vuoka'],
                        ['en:mold', 'fi:muotti'],
                        ['en:home', 'fi:koti'],
                        ['de:klavier', 'en:piano', 'fi:piano'],
                        ['de:konzert', 'en:concerto', 'fi:konsertto'],
                        ['?:fuge'])
        fuge, = meanings
        self.assertMeanings(Meaning.objects.lookup_exact('fuge'), fuge)
        fuge.delete()

    def test_09_lookup_create_extra_letter(self):
        meanings, words = Meaning.objects.lookup_splitting(
            'kotipianon', create_missing=True)
        assert_meanings(['?:kotipianon'],
                        ['en:mold', 'fi:home'],
                        ['en:mold', 'fi:vuoka'],
                        ['en:mold', 'fi:muotti'],
                        ['en:home', 'fi:koti'],
                        ['de:klavier', 'en:piano', 'fi:piano'],
                        ['de:konzert', 'en:concerto', 'fi:konsertto'])

    def test_10_lookup_extra_letter(self):
        n = self.create_meaning('fi:n')
        meanings, words = Meaning.objects.lookup_splitting(
            u'kotipianon', create_missing=False)
        self.assertMeanings(meanings, self.home, self.piano, n)
        self.assertEqual(words, (u'koti', u'piano', u'n'))

    def test_11_lookup_multiple(self):
        meanings, words = Meaning.objects.lookup(['muotti', 'concerto'])
        self.assertMeanings(meanings, self.mold_manufacturing, self.concerto)
        self.assertEqual(words, set(['concerto', 'muotti']))

    def test_12_lookup_multiple_with_compound(self):
        meanings, words = Meaning.objects.lookup(['home', 'pianokonsertto'])
        self.assertMeanings(
            meanings, self.mold_fungus, self.home, self.piano, self.concerto)

    def test_13_lookup_ordered(self):
        meaning_tree, words = Meaning.objects.lookup_ordered(
            ['home', 'pianokonsertto', 'piano', 'home', 'konsertto', 'unknown'])
        self.assertMeaningTree(
            meaning_tree,
            (self.mold_fungus, self.home),
            (self.piano, self.concerto),
            (self.piano,),
            (self.mold_fungus, self.home),
            (self.concerto,),
            ())
        self.assertEqual(words, set([u'konsertto', 'home', 'piano']))

    def test_14_lookup_ordered_create_missing(self):
        meaning_tree, words = Meaning.objects.lookup_ordered(
            ['home', 'beef'], create_missing=True)
        beef = Meaning.objects.get(words__normalized_spelling='beef')
        self.assertMeaningTree(
            meaning_tree,
            (self.mold_fungus, self.home),
            (beef,))
        self.assertEqual(words, set([u'beef', 'home']))

    def test_15_lookup_sentence(self):
        meaning_tree, words = Meaning.objects.lookup_sentence(
            u'home pianokonsertto')
        self.assertMeaningTree(
            meaning_tree,
            (self.mold_fungus, self.home),
            (self.piano, self.concerto))
        self.assertMeanings(
            meaning_tree.flat,
            self.mold_fungus, self.home, self.piano, self.concerto)
        self.assertEqual(words, set([u'konsertto', u'home', u'piano']))


class IndexerTests(TestCase, MeaningHelpers):

    def setUp(self):
        c = self.create_meaning
        self.mold_fungus = c('en:mold', 'fi:home')
        self.home = c('en:home', 'fi:koti')
        self.piano = c('en:piano', 'fi:piano', 'de:klavier')
        self.concerto = c('en:concerto', 'fi:konsertto', 'de:konzert')
        self.sentence = Sentence.objects.create(text=u'klavierkonzert')
        self.sentence.authors.create(name='Goethe')
        self.assertVocabulary(u'de:klavier/1 de:konzert/1 '  #debug
                              u'en:concerto/0 en:home/0 en:mold/0 en:piano/0 '
                              u'fi:home/0 fi:konsertto/0 fi:koti/0 fi:piano/0')
        self.sentence.save()
        self.assertVocabulary(u'None:goethe/1 de:klavier/1 de:konzert/1 '  #debug
                              u'en:concerto/0 en:home/0 en:mold/0 en:piano/0 '
                              u'fi:home/0 fi:konsertto/0 fi:koti/0 fi:piano/0')
        self.goethe = Meaning.objects.lookup_exact('goethe')[0]

    def assertWordFrequency(self, freq, *lang_words):
        for lang_word in lang_words:
            lang, spelling = lang_word.split(':')
            word = Word.objects.get(language=lang or None,
                                    normalized_spelling=spelling)
            self.assertEqual(word.frequency, freq,
                             '%r: %d != %d' % (lang_word, word.frequency, freq))

    def assertIndexEntries(self, queryset, *sequence):
        """
        Asserts that the order and meanings of index entries in the
        `queryset` exactly match those given in the `sequence`.  The
        `sequence` is a list of meanings interspersed with integer
        orders.
        """
        entrydict = {}
        for entry in queryset.order_by('order'):
            entrydict.setdefault(entry.order, set()).add(entry.meaning)
        order = 1
        for item in sequence:
            if isinstance(item, int):
                order = item
                continue
            try:
                entrydict[order].remove(item)
            except KeyError:
                raise AssertionError('%r not in order %d in %r' % (
                        item, order, queryset))
        self.assertEqual(set.union(*entrydict.values()), set())

    def assertVocabulary(self, voc_str):
        words = Word.objects.order_by('language', 'normalized_spelling')
        self.assertEqual(' '.join(unicode(w) for w in words), voc_str)

    def test_01_registry(self):
        """
        The Sentence model should be registered by the ``testapp``
        application.  There might be other entries in the registry
        when the test suite is run as part of a project with other
        apps.
        """
        self.assertTrue(Sentence in registry)
        self.assertEqual(registry[Sentence],  ('authors__name', 'text',))

    def test_02_index_on_post_save(self):
        self.assertIndexEntries(
            (self.sentence.index_entries.all()),
            1, self.goethe, 2, self.piano, self.concerto)

    def test_03_frequencies_updated_on_save(self):
        f=self.assertWordFrequency
        f(0, 'en:mold', 'fi:home', 'en:home', 'fi:koti', 'en:piano', 'fi:piano',
          'en:concerto', 'fi:konsertto')
        f(1, 'de:klavier', 'de:konzert', ':goethe')

    def test_04_raw_save_not_indexed(self):
        s = Sentence(text=u'home pianokonsertto')
        s.save_base(raw=True) # prevent automatic indexing
        self.assertFalse([e.meaning for e in s.index_entries.all()])
        f=self.assertWordFrequency
        f(0, 'fi:home', 'en:home', 'en:piano', 'fi:piano', 'fi:konsertto')
        IndexEntry.objects.create_for_instance(s)
        s.delete()

    def test_05_unindex_instance(self):
        IndexEntry.objects.delete_for_instance(self.sentence)
        self.assertWordFrequency(0, 'de:klavier', 'de:konzert')
        IndexEntry.objects.create_for_instance(self.sentence)

    def test_06_index_instance(self):
        s = Sentence(text=u'home pianokonsertto')
        s.save_base(raw=True) # prevent automatic indexing
        result = IndexEntry.objects.create_for_instance(s)
        self.assertIndexEntries(
            s.index_entries.all(),
            1, self.mold_fungus, self.home, 2, self.piano, self.concerto)
        f=self.assertWordFrequency
        f(1, 'fi:home', 'en:home', 'en:piano', 'fi:piano', 'fi:konsertto')
        s.delete()

    def test_07_add_missing_words_to_index(self):
        self.assertEqual(repr(Meaning.objects.all()),
                         '[<Meaning: 1: en:mold,fi:home>,'
                         ' <Meaning: 2: en:home,fi:koti>,'
                         ' <Meaning: 3: de:klavier,en:piano,fi:piano>,'
                         ' <Meaning: 4: de:konzert,en:concerto,fi:konsertto>,'
                         ' <Meaning: 5: None:goethe>]')
        self.assertVocabulary(u'None:goethe/1 de:klavier/1 de:konzert/1 '
                              u'en:concerto/0 en:home/0 en:mold/0 en:piano/0 '
                              u'fi:home/0 fi:konsertto/0 fi:koti/0 fi:piano/0')
        s = Sentence.objects.create(text=u'Grieg: Concerto for piano')
        self.assertEqual([repr(m) for m in Meaning.objects.all()],
                         ['<Meaning: 1: en:mold,fi:home>',
                          '<Meaning: 2: en:home,fi:koti>',
                          '<Meaning: 3: de:klavier,en:piano,fi:piano>',
                          '<Meaning: 4: de:konzert,en:concerto,fi:konsertto>',
                          '<Meaning: 5: None:goethe>',
                          '<Meaning: 6: None:grieg>',
                          '<Meaning: 7: None:for>'])
        self.assertVocabulary(u'None:for/1 None:goethe/1 None:grieg/1 '
                              u'de:klavier/1 de:konzert/1 en:concerto/1 '
                              u'en:home/0 en:mold/0 en:piano/1 fi:home/0 '
                              u'fi:konsertto/0 fi:koti/0 fi:piano/1')
        grieg = Meaning.objects.get(words__normalized_spelling='grieg')
        self.assertEqual(repr(grieg), '<Meaning: 6: None:grieg>')
        s.delete()

    def test_08_join_meanings(self):
        """
        Join two meanings.
        """
        s1 = Sentence.objects.create(text=u'violin sonata')
        s2 = Sentence.objects.create(text=u'sonaatti viululle')

        m1s = Meaning.objects.lookup_exact(u'sonata')
        self.assertEqual(len(m1s), 1)
        m1 = m1s[0]
        self.assertEqual(repr(m1), '<Meaning: 7: None:sonata>')

        m2s = Meaning.objects.lookup_exact(u'sonaatti')
        self.assertEqual(len(m2s), 1)
        m2 = m2s[0]
        self.assertEqual(repr(m2), '<Meaning: 8: None:sonaatti>')

        assert_meanings(['en:mold', 'fi:home'],
                        ['en:home', 'fi:koti'],
                        ['de:klavier', 'en:piano', 'fi:piano'],
                        ['de:konzert', 'en:concerto', 'fi:konsertto'],
                        ['?:goethe'],
                        ['?:violin'],
                        ['?:sonata'],
                        ['?:sonaatti'],
                        ['?:viululle'])
        assert_index(s1, (1, '?:violin'), (2, '?:sonata'))
        assert_index(s2, (1, '?:sonaatti'), (2, '?:viululle'))

        Meaning.objects.join(m1, m2)

        assert_meanings(['en:mold', 'fi:home'],
                        ['en:home', 'fi:koti'],
                        ['de:klavier', 'en:piano', 'fi:piano'],
                        ['de:konzert', 'en:concerto', 'fi:konsertto'],
                        ['?:goethe'],
                        ['?:violin'],
                        ['?:sonaatti', '?:sonata'],
                        ['?:viululle'])
        assert_index(s1, (1, '?:violin'), (2, '?:sonaatti', '?:sonata'))
        assert_index(s2, (1, '?:sonaatti', '?:sonata'), (2, '?:viululle'))

        self.assertEqual(repr(m1), '<Meaning: 7: None:sonaatti,None:sonata>')
        self.assertEqual(m2.pk, None)
        s1.delete()
        s2.delete()

    def test_09_join_meanings_with_collision(self):
        """
        Join meanings while two of the meanings have an identical
        spelling in the same language.
        """
        s1 = Sentence.objects.create(text=u'violin sonata')
        s2 = Sentence.objects.create(text=u'sonaatti viululle')
        m1 = Meaning.objects.lookup_exact(u'sonata')[0]
        self.assertEqual(repr(m1), '<Meaning: 7: None:sonata>')
        m2 = Meaning.objects.lookup_exact(u'sonaatti')[0]
        self.assertEqual(repr(m2), '<Meaning: 8: None:sonaatti>')
        m3 = Meaning.objects.create(words=[(None, 'sonata')])
        self.assertEqual(repr(m3), '<Meaning: 10: None:sonata>')
        Meaning.objects.join(m1, m2, m3)
        self.assertEqual(repr(m1), '<Meaning: 7: None:sonaatti,None:sonata>')
        self.assertEqual(m2.pk, None)
        self.assertEqual(m3.pk, None)
        s1.delete()
        s2.delete()


class ComplexIndexer_Tests(TestCase, MeaningHelpers):
    def test_01_build_vocabulary(self):
        # meanings Capitalized
        # sentences in_lower_case

        assert_meanings_diff = self.assert_meaning_changes
        
        assert_meanings()  # no meanings initially

        string_quartet = self.new_sentence('string quartet')
        assert_index(string_quartet, [1, '?:string'], [2, '?:quartet'])
        assert_meanings_diff(added=[['?:string'],
                                    ['?:quartet']])

        jousikvartetto = self.new_sentence('jousikvartetto')
        assert_index(jousikvartetto, [1, '?:jousikvartetto'])
        assert_meanings_diff(added=[['?:jousikvartetto']])

        String = self.create_meaning('fi:jousi', 'en:string')
        assert_meanings_diff(added=[['en:string', 'fi:jousi']])
        IndexEntry.objects.index_instance(jousikvartetto)
        assert_index(jousikvartetto, [1, '?:jousikvartetto'])

        # longest match used: not jousi-kvartetto but jousikvartetto
        Quartet = self.create_meaning('fi:kvartetto', 'en:quartet')
        assert_meanings_diff(added=[['en:quartet', 'fi:kvartetto']])
        IndexEntry.objects.index_instance(jousikvartetto)
        assert_index(jousikvartetto, [1, '?:jousikvartetto'])

        # reindex jousikvartetto as jousi-kvartetto
        Meaning.objects.split(self.lookup_one_meaning(u'jousikvartetto'),
                              String, Quartet)
        assert_index(jousikvartetto,
                     [1, 'en:string', 'fi:jousi'],
                     [1, 'en:quartet', 'fi:kvartetto'])
        assert_meanings_diff(removed=[['?:jousikvartetto']])

        quartet_in_g_str = self.new_sentence('Quartet in g (str)')
        assert_index(quartet_in_g_str,
                     [1, '?:quartet'],
                     [1, 'en:quartet', 'fi:kvartetto'],
                     [2, '?:in'],
                     [3, '?:g'],
                     [4, '?:str'])
        assert_meanings_diff(added=[['?:g'], ['?:in'], ['?:str']])

        string_quintet = self.new_sentence('string quintet')
        assert_index(string_quintet,
                     [1, '?:string'], [1, 'en:string', 'fi:jousi'],
                     [2, '?:quintet'])
        assert_meanings_diff(added=[['?:quintet']])

        gintonic = self.new_sentence('gintonic')
        assert_index(gintonic,
                     [1, '?:gintonic'])
        assert_meanings_diff(added=[['?:gintonic']])
