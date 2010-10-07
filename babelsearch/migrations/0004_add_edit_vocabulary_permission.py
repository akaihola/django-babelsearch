# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        ct, created = ContentType.objects.get_or_create(
            model='', app_label='babelsearch', defaults={'name': 'babelsearch'})
        Permission.objects.get_or_create(
            codename='edit_vocabulary', content_type__pk=ct.id,
            defaults={'name': 'Can edit vocabulary', 'content_type': ct})

    def backwards(self, orm):
        Permission.objects.filter(
            content_type__app_label='babelsearch',
            content_type__model='',
            codename='edit_vocabulary').delete()
        ContentType.objects.filter(model='', app_label='babelsearch').delete()


    models = {
        'babelsearch.indexentry': {
            'Meta': {'ordering': "('content_type', 'object_id', 'order')", 'unique_together': "(('content_type', 'object_id', 'order', 'meaning'),)", 'object_name': 'IndexEntry'},
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
        'babelsearch.reindexqueue': {
            'Meta': {'object_name': 'ReindexQueue'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'babelsearch.word': {
            'Meta': {'ordering': "('language', 'normalized_spelling')", 'unique_together': "(('normalized_spelling', 'language'),)", 'object_name': 'Word'},
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
