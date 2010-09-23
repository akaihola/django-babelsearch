from django import forms
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
import operator

from babelsearch.models import Meaning, IndexEntry
from babelsearch.preprocess import lower_without_diacritics
from babelsearch.reindexer import queue_changes


def str_repr(s):
    return repr(unicode(s))[2:-1]


class WordsForm(forms.Form):
    words = forms.CharField(max_length=200,
                            label=_('Add words'),
                            required=False)


class WordsWidget(forms.Textarea):
    def _format_value(self, value):
        if isinstance(value, basestring):
            return value
        return '\n'.join('%s%s' % (lang and '%s:' % lang or '', spelling)
                         for lang, spelling in value)

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return mark_safe(u'<textarea%s>%s</textarea>' % (
            forms.util.flatatt(final_attrs),
            force_unicode(self._format_value(value))))



class MeaningForm(forms.Form):
    meaning = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    words = forms.CharField(widget=WordsWidget(attrs={'cols': 20}),
                            label=_('Translations'),
                            required=False)

    def decode_row(self, row):
        if ':' in row:
            language, word = (item.strip() for item in row.split(':', 1))
            if len(language) != 2:
                raise forms.ValidationError(
                    _('Invalid language code on line: %s' % str_repr(row)))
        else:
            language = None
            word = row
        normalized_spelling = lower_without_diacritics(word)
        if not normalized_spelling:
            raise forms.ValidationError(
                _('No word found on line %s' % str_repr(row)))
        return language, normalized_spelling

    def decode_words(self):
        return set(self.decode_row(row)
                   for row in self.cleaned_data['words'].split())

    def clean_words(self):
        return self.decode_words()

    def clean_meaning(self):
        pk = self.cleaned_data['meaning']
        if pk:
            try:
                Meaning.objects.get(pk=pk)
            except Meaning.DoesNotExist:
                raise forms.ValidationError(_('Meaning with ID %s not found' % pk))
        return pk
        
    def save(self):
        if not self.cleaned_data:
            return None, False
        pk = self.cleaned_data['meaning']
        if pk:
            meaning = Meaning.objects.get(pk=self.cleaned_data['meaning'])
            created = False
        else:
            meaning = Meaning.objects.create()
            created = True
            self.cleaned_data['meaning'] = meaning.pk
        new_words = self.cleaned_data['words']
        old_word_instances = meaning.words.all()
        old_words = set((word.language, word.normalized_spelling)
                        for word in old_word_instances)

        added_words = new_words.difference(old_words)
        meaning.add_words(added_words)

        removed_words = old_words.difference(new_words)
        if removed_words:
            word_criteria = (Q(language=l, normalized_spelling=s)
                             for l, s in removed_words)
            combined_criteria = reduce(operator.or_, word_criteria)
            meaning.words.remove(*meaning.words.filter(combined_criteria))

        return meaning, added_words.union(removed_words)


class BaseMeaningsFormset(forms.formsets.BaseFormSet):
    def save(self):
        changed_meanings = set()
        changed_words = set()
        for form in self.forms:
            meaning, ch_words = form.save()
            if ch_words:
                changed_meanings.add(meaning)
                changed_words.update([w[1]  # only spelling, no language
                                      for w in ch_words])  
        queue_changes(changed_meanings, changed_words)

MeaningsFormset = formset_factory(MeaningForm, formset=BaseMeaningsFormset)
