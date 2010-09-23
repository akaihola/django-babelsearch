from babelsearch.models import ReindexQueue
from babelsearch.tests.settings_helpers import patch_settings
from mock import Mock, patch, patch_object
import os
import stat
import tempfile
import time
import multiprocessing
from unittest import TestCase

from babelsearch.reindexer import (
    pop_changes,
    get_batches_for,
    get_changed_instances,
    reindex_for_meanings)


class PopChanges_Tests(TestCase):
    def test_reads_all(self):
        """babelsearch.reindexer.pop_changes reads all from fifo"""
        ReindexQueue.objects.create(type='meaning.pk', value='1')
        ReindexQueue.objects.create(type='word.normalized_spelling', value='un')
        
        changes = pop_changes()
        
        self.assertEqual(changes, ([u'1'], [u'un']))
       
        
class GetBatchesFor_Tests(TestCase):
    def test_three_batches(self):
        """babelsearch.reindexer.get_batches_for reads 3 batches correctly"""
        model = Mock()
        model.objects.order_by.return_value = range(14)
        batches = get_batches_for(model, size=5)
        self.assertEqual(list(batches.next()), [0, 1, 2, 3, 4])
        self.assertEqual(list(batches.next()), [5, 6, 7, 8, 9])
        self.assertEqual(list(batches.next()), [10, 11, 12, 13])
        self.assertRaises(StopIteration, batches.next)


class GetChangedInstances_Tests(TestCase):
    def setUp(self):
        self.instances = [Mock() for i in range(2)]
        self.instances[0].pk = 0
        self.instances[1].pk = 1

    def get_instance_words(self, instance):
        return (['zero'], ['onetwothree'])[instance.pk]

    def call_get_changed_instances(self,
                                   changed_instance_pks, changed_spellings):
        with patch('babelsearch.reindexer.get_instance_words',
                   self.get_instance_words):
            result = list(get_changed_instances(
                self.instances, changed_instance_pks, changed_spellings))
        return result
        
    def test_meaning_change(self):
        result = self.call_get_changed_instances([0], set())
        self.assertEqual(result, [self.instances[0]])

    def test_word_part(self):
        result = self.call_get_changed_instances([], set(['one']))
        self.assertEqual(result, [self.instances[1]])


class ReindexForMeanings_Tests(TestCase):
    def test_r(self):
        mocks = Mock()
        mocks.Meaning.objects.get_spellings_for.return_value = set(['one'])
        mocks.registry = {mocks.model: ['name']}
        with patch('babelsearch.reindexer.Meaning', mocks.Meaning):
            with patch('babelsearch.indexer.registry', mocks.registry):
                with patch('babelsearch.reindexer.reindex_model_for_meanings',
                           mocks.rmfm):
                    reindex_for_meanings([0], ['one'])
        self.assertEqual(mocks.rmfm.call_args,
                         ((mocks.model, [0], ['one']), {'callback': None}) )

    def todo_test_reindex_model_for_meanings(self):
        """TODO: work in progress"""
        mocks = Mock()
        mocks.get_batches_for.return_value = ['dummy instance']
        mocks.model.objects.filter.return_value.values_list.return_value = ['2']
        with patch('babelsearch.reindexer.get_batches_for',
                   mocks.get_batches_for):
            pass
