from django.test import TestCase

from django.db import IntegrityError

from babelsearch.models import Meaning, Word, IndexEntry
from babelsearch.indexer import registry
from example.testapp.models import Sentence

class MeaningCreationTests(TestCase):

    def test_01_add_empty_meaning(self):
        m = Meaning.objects.create()
        self.assertEqual(list(m.words.all()), [])

    def test_02_add_words_to_meaning(self):
        m = Meaning.objects.create()
        m.words.create(normalized_spelling='home', language='fi')
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: home (fi)>'])
        m.words.create(normalized_spelling='mold', language='en')
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: home (fi)>', '<Word: mold (en)>'])

    def test_03_create_meaning_with_words(self):
        m = Meaning.objects.create(
            words=[('en', 'home'), ('fi', 'koti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: home (en)>', '<Word: koti (fi)>'])
        self.assertEqual(Word.objects.count(), 2)

    def test_04_create_duplicate_word(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: mold (en)>', '<Word: muotti (fi)>'])
        self.assertEqual(Word.objects.count(), 2)
        self.assertEqual(repr(Word.objects.all()[1]), '<Word: muotti (fi)>')

    def test_05_cannot_add_duplicate_word_with_create(self):
        m = Meaning.objects.create(words=[('en', 'mold'), ('fi', 'vuoka')])
        self.assertRaises(IntegrityError, m.words.create,
                          language='en', normalized_spelling='mold')
        self.assertEqual(repr(m), '<Meaning: 1: en:mold,fi:vuoka>')

    def test_06_add_duplicate_word_with_get_or_create(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: mold (en)>', '<Word: muotti (fi)>'])
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
        meanings = tuple(sorted(queryset, key=lambda m: m.pk))
        self.assertEqual(meanings, expected_meanings)

    def create_meaning(self, *words):
        return Meaning.objects.create(
            words=[item.split(':') for item in words])

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

    def test_05_lookup_compound(self):
        self.assertMeanings(
            Meaning.objects.lookup_splitting('pianokonsertto'),
            self.piano, self.concerto)

    def test_06_lookup_unknown_compound(self):
        self.assertFalse(Meaning.objects.lookup_splitting('pianokonsertt'))

    def test_07_lookup_multiple(self):
        self.assertMeanings(Meaning.objects.lookup(['muotti', 'concerto']),
                            self.mold_manufacturing, self.concerto)

    def test_08_lookup_multiple_with_compound(self):
        self.assertMeanings(
            Meaning.objects.lookup(['home', 'pianokonsertto']),
            self.mold_fungus, self.home, self.piano, self.concerto)

    def test_08_lookup_sentence(self):
        self.assertMeanings(
            Meaning.objects.lookup_sentence(u'home pianokonsertto'),
            self.mold_fungus, self.home, self.piano, self.concerto)

class IndexerTests(TestCase, MeaningHelpers):

    def setUp(self):
        c = self.create_meaning
        self.mold_fungus = c('en:mold', 'fi:home')
        self.home = c('en:home', 'fi:koti')
        self.piano = c('en:piano', 'fi:piano', 'de:klavier')
        self.concerto = c('en:concerto', 'fi:konsertto', 'de:konzert')
        self.s1 = Sentence.objects.create(text=u'klavierkonzert')

    def test_01_registry(self):
        self.assertEqual(registry, {Sentence: ('text',)})

    def test_02_index_on_post_save(self):
        self.assertMeanings(
            (e.meaning for e in self.s1.index_entries.all()),
            self.piano, self.concerto)

    def test_03_raw_save_not_indexed(self):
        self.s2 = Sentence(text=u'home pianokonsertto')
        self.s2.save_base(raw=True) # prevent automatic indexing
        self.assertFalse([e.meaning for e in self.s2.index_entries.all()])
        self.s2.delete()

    def test_04_index_instance(self):
        self.s2 = Sentence(text=u'home pianokonsertto')
        self.s2.save_base(raw=True) # prevent automatic indexing
        result = IndexEntry.objects.index_instance(self.s2)
        self.assertMeanings(
            (e.meaning for e in self.s2.index_entries.all()),
            self.mold_fungus, self.home, self.piano, self.concerto)
        self.s2.delete()

    def test_05_match_with_search_terms(self):
        terms = u'pianokonsertto'
        results = IndexEntry.objects.search(terms)
        self.assertEqual(list(repr(m) for m in results),
                         ["<IndexEntry: u'klavierkonzert'[1]"
                          " = 3: de:klavier,en:piano,fi:piano>",
                          "<IndexEntry: u'klavierkonzert'[2]"
                          " = 4: de:konzert,en:concerto,fi:konsertto>"])
