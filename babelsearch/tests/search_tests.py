# -*- coding: utf-8 -*-

from django.test import TestCase

from babelsearch.models import (
    Meaning, Word, IndexEntry,
    get_index_info_for_meanings,
    get_scored_matches, get_scored_matches_for_sentence)
from babelsearch.indexer import registry
from babelsearch.datastruct import SetList
from babelsearch.tests.testapp.models import Sentence

class SearchTests(TestCase):

    def setUp(self):
        c = Sentence.objects.create
        def m(*items):
            words = (item.split(':') for item in items)
            return Meaning.objects.create(words=words)
        self.practical = m(u'en:practical', u'fr:pratique')
        self.school = m(u'en:school', u'fr:ecole')
        self.for_ = m(u'en:for', u'fr:pour')
        self.the = m(u'en:the', u'fr:le', u'fr:la')
        self.viola = m(u'en:viola', u'fr:alto')
        self.laubach_school = c(text=u'Laubach: Practical School for the Viola')
        self.bach = m(u'de:bach')
        self.works = m(u'fr:oeuvres', u'en:works', 'de:werke')
        self.complete = m(u'fr:completes', u'en:complete')
        self.one = m(u':1', u'en:one', u'fr:un', u'fr:une')
        self.twelve = m(u':12', u'en:twelve', u'fr:douze')
        self.dupre = m(u'fr:dupre')
        self.functions = m(u'en:works', 'en:functions', 'fi:toimii')
        self.bach_oeuvres = c(
            text=u'Bach: Oeuvres Completes 1-12 **KTS Bach-Dupre/Oeuvres')
        self.piano = m(u'en:piano', u'de:klavier')
        self.selected = m(u'en:chosen', u'en:selected', 'de:ausgewahlte')
        self.tsaikovski = m(u'fi:tsaikovski')
        self.tsaikovski_werke = c(
            text=u'Tsaikovski: Ausgewählte Klavierwerke 1')

    def test_01_ordered_search(self):
        meaning_tree, found_words = Meaning.objects.lookup_ordered(
            ['ecole', 'pratique'])

    def test_02_get_index_info_for_meanings(self):
        meanings = [self.bach, self.works, self.functions, self.complete]
        result = get_index_info_for_meanings(Sentence, [m.pk for m in meanings])
        bach_id = self.bach_oeuvres.pk
        tsai_id = self.tsaikovski_werke.pk
        self.assertEqual(list(result), [
                {'object_id': bach_id, 'order': 1, 'meaning': self.bach.pk},
                {'object_id': bach_id, 'order': 2, 'meaning': self.works.pk},
                {'object_id': bach_id, 'order': 3, 'meaning': self.complete.pk},
                {'object_id': bach_id, 'order': 7, 'meaning': self.bach.pk},
                {'object_id': bach_id, 'order': 9, 'meaning': self.works.pk},
                {'object_id': tsai_id, 'order': 3, 'meaning': self.works.pk}])

    def test_03_get_scored_matches(self):
        meaning_tree = SetList([[self.bach],
                                [self.functions, self.works],
                                #[self.works, self.functions],
                                [self.complete]])
        result = get_scored_matches(Sentence, meaning_tree)
        self.assertEqual(result, [(75, 2), (25, 3)])

    def test_04_get_scored_matches_for_sentence(self):
        result = get_scored_matches_for_sentence(Sentence,
                                                 u'bach works completes')
        self.assertEqual(result,
                         [{'instance': self.bach_oeuvres, 'score': 75},
                          {'instance': self.tsaikovski_werke, 'score': 25}])
