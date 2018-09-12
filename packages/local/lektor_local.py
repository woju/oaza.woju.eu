import jinja2
import lektor.pluginsystem

class LocalPlugin(lektor.pluginsystem.Plugin):
    name = u'local'
    description = u'A local plugin, random non-reusable hacks.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_setup_env(self, **extra):
        self.env.jinja_env.globals['needs_absurl'] = self.needs_absurl

    def needs_absurl(self, record):
        if record['_model'] == 'error':
            return True
        return None

# vim: ts=4 sts=4 sw=4 et fileencoding=utf-8
