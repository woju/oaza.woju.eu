import datetime
import lektor.pluginsystem

class CurrentDatePlugin(lektor.pluginsystem.Plugin):
    name = u'current-date'
    description = u'Insert current date into template context.'

    def on_setup_env(self, **extra):
        self.env.jinja_env.globals['now'] = datetime.datetime.now()

# vim: ts=4 sts=4 sw=4 et fileencoding=utf-8
