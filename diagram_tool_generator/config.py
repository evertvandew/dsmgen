


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
    pub_dir: str      = ''
    model_name: str   = ''


    def __post_init__(self):
        if not self.model_name:
            self.model_name = os.path.splitext(os.path.basename(self.model_def))[0]

        if self.model_name.endswith('spec'):
            self.model_name = self.model_name[:-4].strip('_')
