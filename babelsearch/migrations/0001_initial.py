# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Word'
        db.create_table('babelsearch_word', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('normalized_spelling', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=5, null=True)),
            ('frequency', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('babelsearch', ['Word'])

        # Adding unique constraint on 'Word', fields ['normalized_spelling', 'language']
        db.create_unique('babelsearch_word', ['normalized_spelling', 'language'])

        # Adding model 'Meaning'
        db.create_table('babelsearch_meaning', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('babelsearch', ['Meaning'])

        # Adding M2M table for field words on 'Meaning'
        db.create_table('babelsearch_meaning_words', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('meaning', models.ForeignKey(orm['babelsearch.meaning'], null=False)),
            ('word', models.ForeignKey(orm['babelsearch.word'], null=False))
        ))
        db.create_unique('babelsearch_meaning_words', ['meaning_id', 'word_id'])

        # Adding model 'IndexEntry'
        db.create_table('babelsearch_indexentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('meaning', self.gf('django.db.models.fields.related.ForeignKey')(related_name='index_entries', to=orm['babelsearch.Meaning'])),
        ))
        db.send_create_signal('babelsearch', ['IndexEntry'])

        # Adding unique constraint on 'IndexEntry', fields ['content_type', 'object_id', 'order', 'meaning']
        db.create_unique('babelsearch_indexentry', ['content_type_id', 'object_id', 'order', 'meaning_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'IndexEntry', fields ['content_type', 'object_id', 'order', 'meaning']
        db.delete_unique('babelsearch_indexentry', ['content_type_id', 'object_id', 'order', 'meaning_id'])

        # Removing unique constraint on 'Word', fields ['normalized_spelling', 'language']
        db.delete_unique('babelsearch_word', ['normalized_spelling', 'language'])

        # Deleting model 'Word'
        db.delete_table('babelsearch_word')

        # Deleting model 'Meaning'
        db.delete_table('babelsearch_meaning')

        # Removing M2M table for field words on 'Meaning'
        db.delete_table('babelsearch_meaning_words')

        # Deleting model 'IndexEntry'
        db.delete_table('babelsearch_indexentry')


    models = {
        'babelsearch.indexentry': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'order', 'meaning'),)", 'object_name': 'IndexEntry'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meaning': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'index_entries'", 'to': "orm['babelsearch.Meaning']"}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'babelsearch.meaning': {
            'Meta': {'object_name': 'Meaning'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'words': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['babelsearch.Word']", 'symmetrical': 'False'})
        },
        'babelsearch.word': {
            'Meta': {'unique_together': "(('normalized_spelling', 'language'),)", 'object_name': 'Word'},
            'frequency': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True'}),
            'normalized_spelling': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['babelsearch']
