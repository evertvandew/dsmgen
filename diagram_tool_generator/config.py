


from dataclasses import dataclass
import os

@dataclass
class Configuration:
    model_def: str
    client_dir: str   = 'public'
    server_dir: str   = 'build'
    dbase_url: str    = 'sqlite:///data/diagrams.sqlite3'
    dbase_uname: str  = ''
    dbase_pwd: str    = ''
    homedir: str      = os.getcwd()