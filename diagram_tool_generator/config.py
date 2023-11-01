


from dataclasses import dataclass


@dataclass
class Configuration:
    model_def: str
    target_dir: str   = 'public'
    dbase_url: str    = 'sqlite:///data/diagrams.sqlite3'
    dbase_uname: str  = ''
    dbase_pwd: str    = ''

