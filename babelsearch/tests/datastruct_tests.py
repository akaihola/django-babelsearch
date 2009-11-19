# -*- coding: utf-8 -*-

from unittest import TestCase

from babelsearch.datastruct import SetList, AutoDiscardDict, PrefixCache
from babelsearch.models import Word

class AutoDiscardDictTests(TestCase):

    def setUp(self):
        self.d = AutoDiscardDict()

    def test_01_set(self):
        self.d[1] = 5
        self.assertEqual(self.d[1], 5)

    def test_02_zero(self):
        self.d[2] = 5
        self.d[2] = 0
        self.assertFalse(2 in self.d)

    def test_03_increment_new(self):
        self.d[3] += 1
        self.assertEqual(self.d[3], 1)

    def test_04_increment_existing(self):
        self.d[4] = 3
        self.d[4] += 1
        self.assertEqual(self.d[4], 4)

    def test_05_decrement_existing(self):
        self.d[5] = 6
        self.d[5] -= 1
        self.assertEqual(self.d[5], 5)

    def test_06_decrement_to_zero(self):
        self.d[6] = 1
        self.d[6] -= 1
        self.assertFalse(6 in self.d)


class SetListTests(TestCase):

    def setUp(self):
        self.setlist = SetList()

    def assertSetList(self, setlist, positions):
        self.assertEqual(
            len(setlist), len(positions),
            'len(%r) [%d] != len(%r) [%d]' % (
                setlist, len(setlist), positions, len(positions)))
        for index, (setlist_position, position) in enumerate(zip(setlist, positions)):
            self.assertEqual(
                set(setlist_position), set(position),
                'got[%d] [%r] != expected[%d] [%r]' % (
                    index, setlist_position, index, position))

    def assertSetListFlat(self, setlist, theset):
        self.assertEqual(set(setlist.flat), set(theset))

    def test_01_add_to_set(self):
        self.setlist[3].add('item1')
        self.assertSetList(self.setlist, [[], [], [], ['item1']])
        self.assertSetListFlat(self.setlist, ['item1'])

    def test_02_truncate(self):
        self.assertEqual(set(self.setlist[3]), set())
        self.assertSetList(self.setlist, [[], [], [], []])
        self.setlist.truncate()
        self.assertSetList(self.setlist, [])

    def test_03_discard_from_set(self):
        self.setlist[3].add('item1')
        self.setlist[3].discard('item1')
        self.assertSetListFlat(self.setlist, [])
        self.assertSetList(self.setlist, [])

    def test_04_assign_set(self):
        self.setlist[2] = ['item1', 'item2']
        self.assertSetList(self.setlist, [[], [], ['item1', 'item2']])

    def test_05_append_set(self):
        self.setlist[0] = []
        self.setlist.append(['item1', 'item2'])
        self.assertSetList(self.setlist, [[], ['item1', 'item2']])

    def test_05_initialize(self):
        data = [['item1'], [], ['item2', 'item3']]
        setlist = SetList(data)
        self.assertSetList(setlist, data)

class PrefixCacheTests(TestCase):

    def setUp(self):
        self.abc = Word.objects.create(normalized_spelling=u'abc')
        self.efg = Word.objects.create(normalized_spelling=u'efg')

    def tearDown(self):
        self.abc.delete()
        self.efg.delete()

    def test_seed_with_no_values(self):
        c = PrefixCache(Word, 'normalized_spelling')
        c.seed([])
        self.assertEqual(c.items(), [])

    def test_seed(self):
        c = PrefixCache(Word, 'normalized_spelling')
        c.seed([u'abx', u'efh'])
        self.assertEqual(sorted(c.items()),
                         [(u'ab', set([u'abc'])),
                          (u'ef', set([u'efg']))])

    def test_add(self):
        c = PrefixCache(Word, 'normalized_spelling')
        c.add(u'ghi')
        self.assertEqual(c.items(), [(u'gh', set([u'ghi']))])

    def test_discard(self):
        c = PrefixCache(Word, 'normalized_spelling')
        c.add(u'jkl')
        c.add(u'mno')
        c.add(u'mnp')
        self.assertEqual(sorted(c.items()),
                         [(u'jk', set([u'jkl'])),
                          (u'mn', set([u'mno', u'mnp']))])
        c.discard(u'jkl')
        c.discard(u'mno')
        self.assertEqual(c.items(), [(u'mn', set([u'mnp'])),
                                     (u'jk', set([]))])

    def test_contains(self):
        c = PrefixCache(Word, 'normalized_spelling')
        c.seed([u'ab-starting-words'])
        self.assertEqual(c.items(), [(u'ab', set([u'abc']))])
        self.assertTrue(c.contains(u'abc'))
        self.assertTrue(c.contains(u'efg'))
        self.assertEqual(c.items(), [(u'ab', set([u'abc'])),
                                     (u'ef', set([u'efg']))])

    def test_instances_with_prefix(self):
        c = PrefixCache(Word, 'normalized_spelling')
        words = c._instances_with_prefix(u'ab')
        self.assertEqual(list(words), [self.abc])
