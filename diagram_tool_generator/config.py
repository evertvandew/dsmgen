


from dataclasses import dataclass


@dataclass
class Configuration:
    model_def: str
    target_dir: str
    dbase_url: str
    dbase_uname: str
    dbase_pwd: str

