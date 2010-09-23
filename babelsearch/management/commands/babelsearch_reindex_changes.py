from django.core.management.base import NoArgsCommand
import os
import time


class Command(NoArgsCommand):
    help = 'Re-index whenever babelsearch vocabulary changes'

    def handle_noargs(self, **options):
        from babelsearch.reindexer import reindex_for_changes, get_trigger_path

        def show_instance(s):
            print s

        last_trigger_time = 0
        trigger_path = get_trigger_path()

        while True:
            print '\nWaiting for vocabulary changes...\n'
            try:
                trigger_time = os.path.getmtime(trigger_path)
            except OSError:
                pass
            else:
                if trigger_time > last_trigger_time:
                    last_trigger_time = trigger_time
                    reindex_for_changes(callback=show_instance)
                    continue
            time.sleep(10)
