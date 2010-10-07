from django.shortcuts import render_to_response
from django.template import RequestContext

from babelsearch.forms import WordsForm, MeaningsFormset
from babelsearch.models import Meaning


def get_tokenization_for(terms):
    result, found_words = Meaning.objects.lookup_sentence(terms)
    return u' '.join(found_words)


def _make_meaning_data(meaning):
    return {'meaning': meaning.pk,
            'words': [(w.language, w.normalized_spelling)
                      for w in meaning.words.all()]}


def edit_vocabulary(request, app_name=None, model_name=None, instance_pk=None):
    template_name = 'babelsearch/edit-vocabulary.html'

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
        words_form = WordsForm(prefix='words')
        meanings_formset = MeaningsFormset(prefix='meanings')

    return render_to_response(template_name,
                              {'words_form': words_form,
                               'meanings_formset': meanings_formset},
                              RequestContext(request));
