import os.path as op
from datalad.support.constraints import EnsureStr

definitions = {
    'datalad.containers.location': {
        'ui': ('question', {
            'title': 'Container location',
            'text': 'path within the dataset where to store containers'}),
        'default': op.join(".datalad", "environments"),
        'type': EnsureStr(),
        'destination': 'dataset'
    },
}
