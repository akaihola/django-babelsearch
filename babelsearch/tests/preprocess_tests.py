# -*- coding: utf-8 -*-

from unittest import TestCase

from babelsearch.preprocess import tokenize, lower_without_diacritics, get_words


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
            [u'saint',
             u'saens',
             u'hommage',
             u'a',
             u"martinu's",
             u'dad',
             u'ss',
             u'34'])
