from pprint import pformat

from babelsearch.models import Meaning


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
        expected_meanings, actual_meanings)


