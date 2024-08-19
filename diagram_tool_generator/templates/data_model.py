from typing import List
<%
"""
    Template for generating the data model for the visual modelling environment.
    The data model will use the SQLAlchemy library.

"""

"""
Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

from enum import EnumType
from dataclasses import fields
import model_definition as md

def get_type(t):
    return generator.get_type(t)

def get_sql_type(t):
    tp = {
        'int': 'Integer',
        'str': 'String',
        'datetime': 'DateTime',
        'time': 'Time',
        'float': 'Float',
        'longstr': 'str',
        'parameter_spec': 'str',
        'parameter_values': 'str'
    }.get(t, '')
    return tp or t

%>

from datetime import datetime, time
import os
import os.path
import json
from enum import IntEnum, auto
from contextlib import contextmanager
from urllib.parse import urlparse
import logging
from dataclasses import dataclass, fields, asdict, field, is_dataclass
from sqlalchemy import (create_engine, Column, Integer, String, DateTime,
     ForeignKey, event, Time, Float, LargeBinary, Enum)
from sqlalchemy.orm import scoped_session, sessionmaker, backref, relationship, reconstructor
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import text


GEN_VERSION = "0.2"

parts = urlparse("${config.dbase_url}")
if parts.scheme == 'sqlite':
    data_dir = './' + os.path.split(parts.path)[0]
else:
    data_dir = None
engine = create_engine("${config.dbase_url}")

def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('pragma foreign_keys=ON')

event.listen(engine, 'connect', _fk_pragma_on_connect)

Session = sessionmaker(engine)


%for cls in [c for c in generator.md.custom_types if isinstance(c, EnumType)]:
class ${cls.__name__}(IntEnum):
%for option in cls:
    ${option.name} = ${option.value}
%endfor
%endfor

class OptionalRef:
    def __init__(self, t):
        self.type = t
    def __execute__(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            if value in ['None', 'null']:
                return None
        return self.t(value)

def get_database_name():
    url = str(engine.url)
    parts = urlparse(url)
    if parts.scheme != 'sqlite':
        return 'unsupported'
    return os.path.split(parts.path)[1]


def changeDbase(url):
    """ Used for testing against a non-standard database """
    global engine, Session
    engine = create_engine(url)
    Session = sessionmaker(engine)


def list_available_databases() -> List[str]:
    """List all available databases in the 'data' subdirectory."""
    if not data_dir:
        return []
    db_files = [f for f in os.listdir(data_dir) if f.endswith('.sqlite3')]
    print('Found databases:', db_files)
    return db_files

def switch_database(db_name: str) -> str:
    """Switch to the specified database using changeDatabase."""
    available_databases = list_available_databases()
    if db_name in available_databases:
        # Construct the database URL
        db_url = f"sqlite:///build/data/{db_name}"
        # Call the existing changeDatabase function
        changeDbase(db_url)
        return f"Switched to database: {db_name}"
    else:
        raise ValueError(f"Database '{db_name}' does not exist.")

class MyBase:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def asdict(self):
        """ Extract a dictionary from this data, e.g. to convert to JSON.
            Direction: Database -> Python code.
        """
        d = {k:getattr(self, k) for k in self.__annotations__.keys()}
        d['__classname__'] = type(self).__name__
        return d

    def post_init(self):
        """ Do necessary modifications before storing data in a database.
            Direction: Python code -> Database.
        """
        pass


Base = declarative_base(cls=MyBase)


@contextmanager
def session_context():
  ''' Return an SQLAlchemy session for interacting with the database.
      The session is suitable for use in a 'with' statement such as :

         with wrapper.sessionContext() as session:
            DoSomething(session)

      The session is committed when it goes out of scope, and rolled-back when an exception
      occurs.
  '''
  session = Session()
  try:
    yield session
    session.commit()
  except:
    logging.exception('Exception while interacting with the database')
    session.rollback()
    raise
  finally:
    session.close()

class Version(Base):
    Id: int = Column(Integer, primary_key = True)
    category: str =  Column(String)
    versionnr: str = Column(String)


def update_db_v0_1(session) -> str:
    """ Update from v0.1 to 0.2. """
    # Add the "category" field to all representations.
    # Added to see the difference between a regular and a laned block.
    session.execute(text(f'ALTER TABLE _messagerepresentation ADD COLUMN "category" INTEGER DEFAULT {ReprCategory.message.value};'))
    session.execute(text(f'ALTER TABLE _relationshiprepresentation ADD COLUMN "category" INTEGER DEFAULT {ReprCategory.relationship.value};'))
    session.execute(text(f'UPDATE version SET versionnr="{GEN_VERSION}" WHERE category="generator";'))
    return GEN_VERSION



def init_db():
    Base.metadata.create_all(bind=engine)
    with session_context() as session:
        versions = session.query(Version).all()
        if len(versions) < 2:
            session.add(Version(category="generator", versionnr=GEN_VERSION))
            session.add(Version(category="model", versionnr=${generator.md.get_version()}))
        else:
            gen_version = [v for v in versions if v.category=='generator'][0].versionnr
            while gen_version != GEN_VERSION:
                updater = globals().get(f"update_db_v{gen_version.replace('.', '_')}")
                gen_version = updater(session)

        % if generator.md.initial_records:
        if session.query(_Entity).count() == 0:
            % for r in generator.md.initial_records:
                ${r}.store(session=session)
            % endfor
        % endif


# ##############################################################################
# # The model contains only a few basic structures, corresponding to the
# # archetypes available in the model definitions.
# #
# # The additional details provided by each subtype are stored in a JSON blob
# # inside the archetype structures. This file provides (de)-serialization.
# #
# # The contents of a diagram are stored in separate structures.

class ReprCategory(IntEnum):
    no_repr = auto()
    block = auto()
    port = auto()
    relationship = auto()
    message = auto()
    laned_block = auto()


class EntityType(IntEnum):
    Block = auto()
    Diagram = auto()
    LogicalElement = auto()
    Port = auto()
    Message = auto()
    Instance = auto()

class _Entity(Base):
    Id: int = Column(Integer, primary_key=True)
    type: int = Column(Enum(EntityType))
    subtype: str = Column(String)
    parent: str = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'), nullable=True)  # For subblocks and ports
    definition: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'), nullable=True)  # For instances
    association: int = Column(Integer, ForeignKey("_relationship.Id", ondelete='CASCADE'), nullable=True)  # For messages & association class.
    order: str = Column(Integer)
    details: str = Column("details", LargeBinary)

class _Relationship(Base):
    Id: int = Column(Integer, primary_key=True)
    subtype: str = Column(String)
    source_id: int  = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    target_id: int  = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    associate_id: int = Column(Integer, ForeignKey("_entity.Id"))
    details: bytes = Column("details", LargeBinary)

class _BlockRepresentation(Base):
    Id: int = Column(Integer, primary_key=True)
    diagram: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    block: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    parent: int = Column(Integer, ForeignKey("_blockrepresentation.Id", ondelete='CASCADE'))
    x: float = Column(Float)
    y: float = Column(Float)
    z: float = Column(Float)  # For placing blocks etc on top of each other
    width: float = Column(Float)
    height: float = Column(Float)
    order: int = Column(Integer)
    orientation: int = Column(Integer)
    styling: str = Column(String)
    category: int = Column(Integer)

    def post_init(self):
        """ In the database, styling is stored as a string. """
        if isinstance(self.styling, dict):
            # Using `eval` is insecure, parse the string directly.
            self.styling = json.dumps(self.styling) if self.styling else ''

    def asdict(self):
        """ When converting to json, format the styling as a string """
        result = Base.asdict(self)
        result['styling'] = json.loads(self.styling) if self.styling else {}
        result['__classname__'] = type(self).__name__
        return result

class _MessageRepresentation(Base):
    Id: int = Column(Integer, primary_key=True)
    diagram: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    message: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    parent: int = Column(Integer, ForeignKey("_relationshiprepresentation.Id", ondelete='CASCADE'))
    x: float = Column(Float)
    y: float = Column(Float)
    z: float = Column(Float)  # For placing blocks etc on top of each other
    order: int = Column(Integer)
    orientation: float = Column(Float)
    direction: int = Column(Integer)
    styling: str = Column(String)
    category: int = Column(Integer)

    def post_init(self):
        """ In the database, styling is stored as a string. """
        if isinstance(self.styling, dict):
            # Using `eval` is insecure, parse the string directly.
            self.styling = json.dumps(self.styling) if self.styling else ''

    def asdict(self):
        """ When converting to json, format the styling as a string """
        result = Base.asdict(self)
        result['styling'] = json.loads(self.styling) if self.styling else {}
        result['__classname__'] = type(self).__name__
        return result

class _RelationshipRepresentation(Base):
    Id: int = Column(Integer, primary_key=True)
    diagram: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    relationship: int = Column(Integer, ForeignKey("_relationship.Id", ondelete='CASCADE'))
    source_repr_id: int = Column(Integer, ForeignKey("_blockrepresentation.Id", ondelete='CASCADE'))
    target_repr_id: int = Column(Integer, ForeignKey("_blockrepresentation.Id", ondelete='CASCADE'))
    routing: bytes = Column(String)       # JSON list of Co-ordinates of nodes
    z: float = Column(Float)                   # For ensuring the line goes over the right blocks.
    styling: str = Column(String)
    category: int = Column(Integer)

    def post_init(self):
        """ In the database, styling is stored as a string. """
        if isinstance(self.styling, dict):
            self.styling = json.dumps(self.styling) if self.styling else ''

    def asdict(self):
        """ When converting to json, format the styling as a string """
        result = super().asdict()
        result['styling'] = json.loads(self.styling) if result['styling'] else {}
        result['__classname__'] = type(self).__name__
        return result


# ##############################################################################
# # Helper for serializing classes.
# # For deserializing, all elements must consume the json in the constructor.

class ExtendibleJsonEncoder(json.JSONEncoder):
    """ A JSON encoder that supports dataclasses and implements a protocol for customizing
        the generation process.
    """
    def default(self, o):
        """ We have three tricks to jsonify objects that are not normally supported by JSON.
            * Dataclass instances are serialised as dicts.
            * For objects that define a __json__ method, that method is called for serialisation.
            * For other objects, the str() protocol is used, i.e. the __str__ method is called.
        """
        if hasattr(o, '__json__'):
            return o.__json__()
        if is_dataclass(o):
            result = {k.name: o.__dict__[k.name] for k in fields(o)}
            result['__classname__'] = type(o).__name__
            return result
        if isinstance(o, Enum):
            return int(o)
        if isinstance(o, bytes):
            return o.decode('utf8')
        return str(o)


# ##############################################################################
# # Custom data classes for handling the custom modelling entities.


class WrongType(RuntimeError): pass
class NotFound(RuntimeError): pass


class longstr(str): pass
class parameter_spec(str): pass
class parameter_values(str): pass

class AWrapper:
    def store(self, session=None, accept_id=False):
        """

        :param session:
        :param accept_id: If true, add records that have the Id set. This is used in testing only.
        :return:
        """
        if session is None:
            with session_context() as session:
                self.store(session, accept_id=accept_id)
        else:
            if (not accept_id) and self.Id and int(self.Id):
                self.update()

            data_bytes = self.asjson()
            table = self.get_db_table()
            # Add the record to the database to get its ID.
            record = table(**self.extract_record_values(), details=data_bytes)
            session.add(record)
            session.commit()        # Intermediate commit to determine the ID
            # Update the original data with ID the record got from the dbase.
            self.Id = record.Id
            data_bytes = self.asjson()
            record.details = data_bytes
            session.commit()

    def extract_record_values(self):
        """ Children of AWrapper are stored in two parts: a standard part that is stored in fields the relational
            database can work with, and a flexible part where additional data is stored in a JSON string.
            This function retrieves the standard part to be stored in separate record fields. This depends on the
            table in which the records are stored, thus this is a "virtual" function.
        """
        raise NotImplementedError()

    def delete(self):
        with session_context() as session:
            table = self.get_db_table()
            session.query(table).filter_by(Id=self.Id).delete()

    def asjson(self):
        return json.dumps(self, cls=ExtendibleJsonEncoder).encode('utf8')

    def asdict(self):
        d = asdict(self)
        d['__classname__'] = type(self).__name__
        return d

    @classmethod
    def decode(cls, record):
        if record is None:
            raise NotFound()
        if record.subtype != cls.__name__:
            raise WrongType()
        details = record.details if isinstance(record.details, str) else record.details.decode('utf8')
        data_dict = json.loads(details)
        assert data_dict['__classname__'] == cls.__name__
        del data_dict['__classname__']
        return cls(**data_dict)


    @classmethod
    def retrieve(cls, Id, session=None):
        if session is None:
            with session_context() as session:
                return cls.retrieve(Id, session=session)
        record = session.query(cls.get_db_table()).filter_by(Id=Id).first()
        return cls.decode(record)

    def update(self, session=None):
        if session is None:
            with session_context() as session:
                return self.update(session)
        else:
            record = session.query(self.get_db_table()).filter_by(Id=self.Id).first()
            data_bytes = self.asjson()
            if record.details != data_bytes:
                record.details = data_bytes
                for key, value in self.extract_record_values().items():
                    if getattr(record, key) != value:
                        setattr(record, key, value)

    @staticmethod
    def load_from_db(record):
        typename = record.subtype
        cls = globals().get(typename)
        details = record.details if isinstance(record.details, str) else record.details.decode('utf8')
        data_dict = json.loads(details)
        assert typename == data_dict['__classname__']
        data_dict = {k:v for k,v in data_dict.items() if k != '__classname__'}
        return cls(**data_dict)


@dataclass
class ABlock(AWrapper):
    order: int = 0
    @staticmethod
    def get_db_table():
        return _Entity
    @classmethod
    def get_entity_type(cls):
        return EntityType.Block
    def extract_record_values(self):
        return {
            'type': self.get_entity_type(),
            'subtype': self.__class__.__name__,
            'parent': getattr(self, 'parent', None),
            'association': getattr(self, 'association', None),
            'definition': None,
            'order': self.order
        }

@dataclass
class AInstance(ABlock):
    parameters: str = '{}'
    @classmethod
    def get_entity_type(cls):
        return EntityType.Instance
    def extract_record_values(self):
        return {
            'type': self.get_entity_type(),
            'subtype': self.__class__.__name__,
            'parent': getattr(self, 'parent', None),
            'definition': self.definition,
            'order': self.order
        }

class ARelationship(AWrapper):
    @staticmethod
    def get_db_table():
        return _Relationship
    def extract_record_values(self):
        return {
            'subtype':       self.__class__.__name__,
            'source_id':     self.source,
            'target_id':     self.target,
            'associate_id':  getattr(self, 'association', None)
        }

@dataclass
class APort(ABlock):
    orientation: int = 0
    @classmethod
    def get_entity_type(cls):
        return EntityType.Port


class ADiagram(ABlock):
    @classmethod
    def get_entity_type(cls):
        return EntityType.Diagram

class ALogicalElement(ABlock):
    @classmethod
    def get_entity_type(cls):
        return EntityType.LogicalElement

class AMessage(ABlock):
    @classmethod
    def get_entity_type(cls):
        return EntityType.Message

    # Generated dataclasses
% for entity in generator.ordered_items:
<%
    stereotype = 'ADiagram' if entity in generator.md.diagrams else \
                 'AInstance' if entity in generator.md.instance_of else \
                 'ABlock' if entity in generator.md.blocks else \
                 'ARelationship' if entity in generator.md.relationship else \
                 'APort' if entity in generator.md.port else \
                 'ALogicalElement'
%>
@dataclass
class ${entity.__name__}(${stereotype}):
    Id: int = 0
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${get_type(f.type)} = ${generator.get_default(f.type)}
    % endfor
    %if generator.md.is_message(entity):
    association: int = None
    %endif

% endfor

if __name__ == '__main__':
    init_db()