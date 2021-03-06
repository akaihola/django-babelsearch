# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Word.indexable'
        db.add_column('babelsearch_word', 'indexable', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Word.indexable'
        db.delete_column('babelsearch_word', 'indexable')


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
            'indexable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
