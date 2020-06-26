import pathlib
import os

application_root = pathlib.Path(__file__).parent.absolute()
http_root = application_root.joinpath('http_server')
secret_key = b'6t9UfLLI11L3POeFym6ywXG5Y9rhGITZ1A02rUY_vLo='
env = os.environ.get('ENV', 'development')
