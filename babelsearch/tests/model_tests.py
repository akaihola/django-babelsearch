from django.test import TestCase

from django.db import IntegrityError
from django.db.models import F

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
                         ['<Word: home (fi/0)>'])
        m.words.create(normalized_spelling='mold', language='en')
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: home (fi/0)>', '<Word: mold (en/0)>'])

    def test_03_create_meaning_with_words(self):
        m = Meaning.objects.create(
            words=[('en', 'home'), ('fi', 'koti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: home (en/0)>', '<Word: koti (fi/0)>'])
        self.assertEqual(Word.objects.count(), 2)

    def test_04_create_duplicate_word(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: mold (en/0)>', '<Word: muotti (fi/0)>'])
        self.assertEqual(Word.objects.count(), 2)
        self.assertEqual(repr(Word.objects.all()[1]), '<Word: muotti (fi/0)>')

    def test_05_cannot_add_duplicate_word_with_create(self):
        m = Meaning.objects.create(words=[('en', 'mold'), ('fi', 'vuoka')])
        self.assertRaises(IntegrityError, m.words.create,
                          language='en', normalized_spelling='mold')
        self.assertEqual(repr(m), '<Meaning: 1: en:mold,fi:vuoka>')

    def test_06_add_duplicate_word_with_get_or_create(self):
        m = Meaning.objects.create(
            words=[('en', 'mold'), ('fi', 'muotti')])
        self.assertEqual([repr(w) for w in m.words.all()],
                         ['<Word: mold (en/0)>', '<Word: muotti (fi/0)>'])
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

    def test_05_lookup_compound_debug1(self):
        meanings, words = Meaning.objects.lookup_splitting(u'konsertto')
        self.assertMeanings(meanings, self.concerto)
        self.assertEqual(words, [u'konsertto'])

    def test_06_lookup_compound_debug2(self):
        meanings, words = Meaning.objects.lookup_splitting('piano', 'konsertto')
        self.assertMeanings(meanings, self.piano, self.concerto)
        self.assertEqual(words, [u'konsertto', 'piano'])

    def test_07_lookup_compound(self):
        meanings, words = Meaning.objects.lookup_splitting('pianokonsertto')
        self.assertMeanings(meanings, self.piano, self.concerto)
        self.assertEqual(words, [u'konsertto', 'piano'])

    def test_08_lookup_unknown_compound(self):
        meanings, words = Meaning.objects.lookup_splitting('pianokonsertt')
        self.assertMeanings(meanings)
        self.assertEqual(words, [])

    def test_09_lookup_create_unknown(self):
        meanings, words = Meaning.objects.lookup_splitting(
            'fuge', create_missing=True)
        self.assertEqual(meanings.count(), 1)
        self.assertEqual(words, [u'fuge'])
        fuge = meanings[0]
        self.assertEqual(repr(fuge), '<Meaning: 7: None:fuge>')
        self.assertMeanings(Meaning.objects.lookup_exact('fuge'), fuge)
        fuge.delete()

    def test_10_lookup_multiple(self):
        meanings, words = Meaning.objects.lookup(['muotti', 'concerto'])
        self.assertMeanings(meanings, self.mold_manufacturing, self.concerto)
        self.assertEqual(words, ['muotti', 'concerto'])

    def test_11_lookup_multiple_with_compound(self):
        meanings, words = Meaning.objects.lookup(['home', 'pianokonsertto'])
        self.assertMeanings(
            meanings, self.mold_fungus, self.home, self.piano, self.concerto)

    def test_12_lookup_sentence(self):
        meanings, words = Meaning.objects.lookup_sentence(
            u'home pianokonsertto')
        self.assertMeanings(
            meanings, self.mold_fungus, self.home, self.piano, self.concerto)
        self.assertEqual(words, [u'home', u'konsertto', u'piano'])

class IndexerTests(TestCase, MeaningHelpers):

    def setUp(self):
        c = self.create_meaning
        self.mold_fungus = c('en:mold', 'fi:home')
        self.home = c('en:home', 'fi:koti')
        self.piano = c('en:piano', 'fi:piano', 'de:klavier')
        self.concerto = c('en:concerto', 'fi:konsertto', 'de:konzert')
        self.sentence = Sentence.objects.create(text=u'klavierkonzert')

    def assertWordFrequency(self, freq, *lang_words):
        for lang_word in lang_words:
            lang, spelling = lang_word.split(':')
            word = Word.objects.get(language=lang, normalized_spelling=spelling)
            self.assertEqual(word.frequency, freq,
                             '%r: %d != %d' % (lang_word, word.frequency, freq))

    def test_01_registry(self):
        self.assertEqual(registry, {Sentence: ('text',)})

    def test_02_index_on_post_save(self):
        self.assertMeanings(
            (e.meaning for e in self.sentence.index_entries.all()),
            self.piano, self.concerto)

    def test_03_frequencies_updated_on_save(self):
        f=self.assertWordFrequency
        f(0, 'en:mold', 'fi:home', 'en:home', 'fi:koti', 'en:piano', 'fi:piano',
          'en:concerto', 'fi:konsertto')
        f(1, 'de:klavier', 'de:konzert')

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
        self.assertMeanings(
            (e.meaning for e in s.index_entries.all()),
            self.mold_fungus, self.home, self.piano, self.concerto)
        f=self.assertWordFrequency
        f(1, 'fi:home', 'en:home', 'en:piano', 'fi:piano', 'fi:konsertto')
        s.delete()

    def test_07_match_with_search_terms(self):
        terms = u'pianokonsertto'
        results = IndexEntry.objects.search(terms)
        self.assertEqual(list(repr(m) for m in results),
                         ["<IndexEntry: u'klavierkonzert'[1]"
                          " = 3: de:klavier,en:piano,fi:piano>",
                          "<IndexEntry: u'klavierkonzert'[2]"
                          " = 4: de:konzert,en:concerto,fi:konsertto>"])
