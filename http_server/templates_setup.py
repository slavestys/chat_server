from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

jinja_env = Environment(
    loader=FileSystemLoader(config.http_root.joinpath('templates')),
    autoescape=select_autoescape(['html', 'xml']),
    variable_start_string='{$',
    variable_end_string='$}'
)
