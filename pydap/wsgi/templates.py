from paste.script import templates

class DapServerTemplate(templates.Template):

    egg_plugins = ['pydap']
    summary = 'A basic pydap server installation.'
    _template_dir = 'template'
    use_cheetah = False

    def post(self, command, output_dir, vars):
        if command.verbose:
            print '*'*72
            print '* Run "paster serve %s/server.ini" to run' % output_dir
            print '* the DAP server on http://localhost:8001/'
            print '*'*72
