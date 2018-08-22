#!/usr/bin/env python3

import sys
import lektor.project

def iter_records(record):
    yield record

    for child in record.pad.query(record.path):
        yield from iter_records(child)

def main():
    project = lektor.project.Project.discover()
    env = project.make_env()
    pad = env.new_pad()

    records = iter_records(pad.get('/'))
    main = next(records)
    reference = main['vim']

    print('reference modeline: {!r}'.format(reference))
    for record in records:
        if not 'body' in record or not record['body']:
            continue
        if not 'vim' in record:
            print('{}: no modeline'.format(record.path))
            continue
        if record['vim'] != reference:
            print('{}: invalid modeline {!r}'.format(record.path, record['vim']))
            
if __name__ == '__main__':
    sys.exit(main())

# vim: ts=4 sts=4 sw=4 et
