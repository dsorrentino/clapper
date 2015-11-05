#!/usr/bin/env python

import glob
import sys


# Import explicitly in this order to fix the import issues:
# https://bugzilla.redhat.com/show_bug.cgi?id=1065251
import ansible.playbook
import ansible.constants as C
import ansible.utils.template
from ansible import errors
from ansible import callbacks
from ansible import utils
from ansible.color import ANSIBLE_COLOR, stringc
from ansible.callbacks import display

import yaml


def die(msg):
    print msg
    sys.exit(1)

def validations():
    paths = glob.glob('playbooks/*.yaml')
    result = []
    for validation_path in sorted(paths):
        with open(validation_path) as f:
            validation = yaml.safe_load(f.read())
            result.append({
                'path': validation_path,
                'name': validation[0]['vars']['metadata']['name']
            })
    return result

class SilentPlaybookCallbacks(object):
    ''' Unlike callbacks.PlaybookCallbacks this doesn't print to stdout. '''

    def __init__(self, verbose=False):
        pass

    def on_start(self):
        callbacks.call_callback_module('playbook_on_start')

    def on_notify(self, host, handler):
        callbacks.call_callback_module('playbook_on_notify', host, handler)

    def on_no_hosts_matched(self):
        callbacks.call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        callbacks.call_callback_module('playbook_on_no_hosts_remaining')

    def on_task_start(self, name, is_conditional):
        callbacks.call_callback_module('playbook_on_task_start', name, is_conditional)

    def on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        callbacks.call_callback_module( 'playbook_on_vars_prompt', varname, private=private, prompt=prompt, encrypt=encrypt, confirm=confirm, salt_size=salt_size, salt=None, default=default)

    def on_setup(self):
        callbacks.call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        callbacks.call_callback_module('playbook_on_import_for_host', host, imported_file)

    def on_not_import_for_host(self, host, missing_file):
        callbacks.call_callback_module('playbook_on_not_import_for_host', host, missing_file)

    def on_play_start(self, name):
        callbacks.call_callback_module('playbook_on_play_start', name)

    def on_stats(self, stats):
        callbacks.call_callback_module('playbook_on_stats', stats)



def run_validation(validation):
    stats = callbacks.AggregateStats()
    playbook_callbacks = SilentPlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_callbacks = callbacks.DefaultRunnerCallbacks()
    playbook = ansible.playbook.PlayBook(
        playbook=validation['path'],
        host_list='hosts',  # TODO: shouldn't be hardcoded
        stats=stats,
        callbacks=playbook_callbacks,
        runner_callbacks=runner_callbacks)
    result = playbook.run()
    print repr(result)
    def success(status):
        return status['failures'] == 0 and status['unreachable'] == 0
    for host, status in result.items():
        status_msg = 'SUCCESS' if success(status) else 'FAILED'
        print host, status_msg
    print "Overall success:", all(success(status) for status in result.values())

def command_list(**args):
    for i, validation in enumerate(validations()):
        print "%d. %s (%s)" % (i + 1, validation['name'], validation['path'])


def command_run(*args):
    if len(args) != 1:
        die("You must pass one argument: the validation ID.")
    try:
        index = int(args[0]) - 1
    except ValueError:
        die("Validation ID must be a number.")
    if index < 0:
        die("Validation ID must be a positive number.")
    try:
        validation = validations()[index]
    except IndexError:
        die("Invalid validation ID.")
        sys.exit(1)
    print "Running validation '%s'" % validation['name']
    run_validation(validation)


def unknown_command(*args):
    die("Unknown command")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
