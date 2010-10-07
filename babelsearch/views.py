from django.db.models import get_model
from django.shortcuts import render_to_response
from django.template import RequestContext

from babelsearch.forms import WordsForm, MeaningsFormset
from babelsearch.models import Meaning
from babelsearch.preprocess import get_instance_text, get_words


def get_tokenization_for(terms):
    result, found_words = Meaning.objects.lookup_sentence(terms)
    return u' '.join(found_words)


def _make_meaning_data(meaning):
    return {'meaning': meaning.pk,
            'words': [(w.language, w.normalized_spelling)
                      for w in meaning.words.all()]}


def edit_vocabulary(request, app_name=None, model_name=None, instance_pk=None):
    template_name = 'babelsearch/edit-vocabulary.html'

    meanings_data = None
    text = None

    if request.method == 'POST':
        words_form = WordsForm(request.POST, prefix='words')
        meanings_formset = MeaningsFormset(request.POST, prefix='meanings')
        if meanings_formset.is_valid():
            meanings_formset.save()
            meanings_data = [d for d in meanings_formset.cleaned_data if d]
            old_meaning_pks = [meaning['meaning'] for meaning in meanings_data
                               if meaning]

            if words_form.is_valid():
                words = words_form.cleaned_data['words'].split()
                new_meanings = Meaning.objects.filter(
                    words__normalized_spelling__in=words).distinct()
                for meaning in new_meanings:
                    if meaning.pk not in old_meaning_pks:
                        meanings_data.append(_make_meaning_data(meaning))
                meanings_formset = MeaningsFormset(initial=meanings_data,
                                                   prefix='meanings')
    else:
        if app_name and model_name and instance_pk:
            # pre-populate formset with meanings of the given indexed
            # model instance
            model = get_model(app_name, model_name)
            instance = model._default_manager.get(pk=instance_pk)
            text = get_instance_text(instance)
            words = get_words(text)
            ordered_meanings, found_words = Meaning.objects.lookup_ordered(
                words, create_missing=False)
            meanings_data = []
            for word in ordered_meanings:
                for meaning in word:
                    meanings_data.append(_make_meaning_data(meaning))
        words_form = WordsForm(prefix='words')
        meanings_formset = MeaningsFormset(initial=meanings_data,
                                           prefix='meanings')

    return render_to_response(template_name,
                              {'words_form': words_form,
                               'meanings_formset': meanings_formset,
                               'analyzed_text': text},
                              RequestContext(request));
