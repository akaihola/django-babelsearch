from django.core.management.base import NoArgsCommand
from optparse import make_option
import os
import time


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--once', '-o', action='store_true', dest='once',
            help='Run reindexing only once and quit.'),
    )
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
                    work_done = reindex_for_changes(callback=show_instance)
                    if work_done and options.get('once', False):
                        break
                    continue
            time.sleep(10)
