# -*- coding: utf-8 -*-

from django.test import TestCase

from babelsearch.datastruct import SetList, AutoDiscardDict

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
        self.ma = SetList()

    def assertSetList(self, ma, positions):
        self.assertEqual(
            len(ma), len(positions),
            'len(%r) [%d] != len(%r) [%d]' % (
                ma, len(ma), positions, len(positions)))
        for index, (ma_position, position) in enumerate(zip(ma, positions)):
            self.assertEqual(
                set(ma_position), set(position),
                'got[%d] [%r] != expected[%d] [%r]' % (
                    index, ma_position, index, position))

    def assertSetListFlat(self, ma, meanings):
        self.assertEqual(set(ma.flat), set(meanings))

    def test_01_add_meaning(self):
        self.ma[3].add('item1')
        self.assertSetList(self.ma, [[], [], [], ['item1']])
        self.assertSetListFlat(self.ma, ['item1'])

    def test_02_truncate(self):
        self.assertEqual(set(self.ma[3]), set())
        self.assertSetList(self.ma, [[], [], [], []])
        self.ma.truncate()
        self.assertSetList(self.ma, [])

    def test_03_discard_meaning(self):
        self.ma[3].add('item1')
        self.ma[3].discard('item1')
        self.assertSetListFlat(self.ma, [])
        self.assertSetList(self.ma, [])

    def test_04_assign_meanings(self):
        self.ma[2] = ['item1', 'item2']
        self.assertSetList(self.ma, [[], [], ['item1', 'item2']])

    def test_05_append_set(self):
        self.ma[0] = []
        self.ma.append(['item1', 'item2'])
        self.assertSetList(self.ma, [[], ['item1', 'item2']])

    def test_05_initialize(self):
        data = [['item1'], [], ['item2', 'item3']]
        ma = SetList(data)
        self.assertSetList(ma, data)
