import datetime
import itertools
import os
import subprocess

import lektor.pluginsystem


class GitCommit(object):
    def __init__(self, line):
        self.commit, timestamp = line.split(' ', 1)
        self.timestamp = datetime.datetime.strptime(timestamp,
            '%Y-%m-%d %H:%M:%S %z')

    @classmethod
    def rev_list(cls, *filenames, **kwargs):
        argv = ['git', 'rev-list', '--pretty=tformat:%H %ai']
        argv.extend('--{}={}'.format(k.replace('_', '-'), v)
            for k, v in kwargs.items())
        argv.append('HEAD')
        if filenames:
            argv.append('--')
            argv.extend(filenames)

        for line in subprocess.check_output(argv).decode().strip().split('\n'):
            if not line or line.startswith('commit '):
                continue
            yield cls(line)

    def __eq__(self, other):
        return self.commit == other.commit

    def __hash__(self):
        return hash(self.commit)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

def get_last_revision(record):
    roots = set(GitCommit.rev_list(max_parents=0))

    candidate = min(roots)  # oldest root

    for filename in itertools.chain(
            record.iter_source_filenames(),
            itertools.chain.from_iterable(attachment.iter_source_filenames()
                for attachment in record.attachments)):
        if not os.path.exists(filename):
            continue

        try:
            commit = next(GitCommit.rev_list(filename, max_count=1))
        except StopIteration:
            continue

        if commit > candidate:
            candidate = commit

    if candidate in roots:
        return None

    return candidate


class CurrentDatePlugin(lektor.pluginsystem.Plugin):
    name = u'current-date'
    description = u'Insert current date into template context.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_setup_env(self, **extra):
        self.env.jinja_env.globals['now'] = datetime.datetime.now()
        self.env.jinja_env.globals['last_revision'] = get_last_revision

# vim: ts=4 sts=4 sw=4 et fileencoding=utf-8
