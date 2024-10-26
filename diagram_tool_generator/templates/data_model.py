from typing import List, Self, Optional, Dict, Any
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
from sqlalchemy.engine import Engine
from sqlalchemy.engine.cursor import CursorResult
from client_src.storable_element import ReprCategory

GEN_VERSION = "0.5"

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


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@contextmanager
def session_context(factory = None):
  ''' Return an SQLAlchemy session for interacting with the database.
      The session is suitable for use in a 'with' statement such as :

         with wrapper.sessionContext() as session:
            DoSomething(session)

      The session is committed when it goes out of scope, and rolled-back when an exception
      occurs.
  '''
  factory = factory or Session
  session = factory()
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
    """ Update from v0.1 (to 0.2.) """
    # Add the "category" field to all representations.
    # Added to see the difference between a regular and a laned block.
    session.execute(text(f'ALTER TABLE _messagerepresentation ADD COLUMN "category" INTEGER DEFAULT {ReprCategory.message.value};'))
    session.execute(text(f'ALTER TABLE _relationshiprepresentation ADD COLUMN "category" INTEGER DEFAULT {ReprCategory.relationship.value};'))
    session.execute(text(f'UPDATE version SET versionnr="{GEN_VERSION}" WHERE category="generator";'))
    return "0.2"

def update_db_v0_2(session):
    """ Update from v0.2 (to 0.3.) """
    # Add the lane_length field to the BlockRepresentation.
    session.execute(text(f'ALTER TABLE _blockrepresentation ADD COLUMN "lane_length" FLOAT DEFAULT 0.0;'))
    return "0.3"

def update_db_v0_3(session):
    """ Update from v0.3 (to 0.4.) """
    # Add the anchor_positions and anchor_sizes field to the BlockRepresentation.
    session.execute(text(f'ALTER TABLE _relationshiprepresentation ADD COLUMN "anchor_positions" STRING DEFAULT "";'))
    session.execute(text(f'ALTER TABLE _relationshiprepresentation ADD COLUMN "anchor_sizes" STRING DEFAULT "";'))
    return "0.4"
def update_db_v0_4(session):
    session.execute(text(f'ALTER TABLE _relationshiprepresentation RENAME COLUMN "anchor_positions" TO "anchor_offsets";'))
    return "0.5"
def update_db_v0_5(session):
    # Re-use the _blockrepresentation table as the basis for the _representation.
    session.execute(
        text(f'ALTER TABLE _blockrepresentation RENAME COLUMN "block" TO "entity";'))
    session.execute(text('ALTER TABLE _blockrepresentation ADD COLUMN "link1" INTEGER'))
    session.execute(text('ALTER TABLE _blockrepresentation ADD COLUMN "link2" INTEGER'))
    session.execute(text('ALTER TABLE _blockrepresentation ADD COLUMN "link3" INTEGER'))
    session.execute(text('ALTER TABLE _blockrepresentation ADD COLUMN "model_class" STRING'))
    session.execute(text('ALTER TABLE _blockrepresentation ADD COLUMN "details" BLOB'))
    session.execute(text('ALTER TABLE _blockrepresentation  RENAME TO "_entity"'))

    #

    # Create _entities for all representations.
    result = session.execute(text('SELECT * FROM _relationship;'))
    keys = result.keys()
    new_entities = []
    for data in result:
        d = dict(zip(keys, data))
        new_entities.append(dict(
            type='Relationship',
            subtype=d['subtype'],
            details=json.dumps(dict(
                order=0,
                source=d['source_id'],
                target=d['target_id'],
                name=d['name'],
                parent=d['parent'],
                __classname__=d['__classname__']
            ))
        ))

    for new_entitie in new_entities.items():
        session.execute(text(''))

    # Replace all instance objects with instance representations

    # Remove the definition and association field
    session.execute(text(f'ALTER TABLE _entity DELETE COLUMN "definition";'))
    session.execute(text(f'ALTER TABLE _entity DELETE COLUMN "association";'))

def init_db(e=None):
    global engine
    e = e or engine
    Base.metadata.create_all(bind=e)
    with session_context(factory=sessionmaker(e)) as session:
        versions = session.query(Version).all()
        if len(versions) < 2:
            session.add(Version(category="generator", versionnr=GEN_VERSION))
            session.add(Version(category="model", versionnr=${generator.md.get_version()}))
        else:
            gen_version = [v for v in versions if v.category=='generator'][0]
            while gen_version.versionnr != GEN_VERSION:
                updater = globals().get(f"update_db_v{gen_version.versionnr.replace('.', '_')}")
                gen_version.versionnr = updater(session)

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


class EntityType(IntEnum):
    Block = auto()
    Relationship = auto()
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
    order: str = Column(Integer)
    details: str = Column("details", LargeBinary)

@dataclass
class _Representation(Base):
    Id: int = Column(Integer, primary_key=True)
    subtype: str = Column(String)       # Holds the role this representation has in the model.
    diagram: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    entity: int = Column(Integer, ForeignKey("_entity.Id", ondelete='CASCADE'))
    parent: int = Column(Integer, ForeignKey("_representation.Id", ondelete='CASCADE'))
    link1: int = Column(Integer, ForeignKey("_representation.Id", ondelete='SET NULL'))
    link2: int = Column(Integer, ForeignKey("_representation.Id", ondelete='SET NULL'))
    link3: int = Column(Integer, ForeignKey("_representation.Id", ondelete='SET NULL'))
    order: int = Column(Integer)
    category: int = Column(Enum(ReprCategory))
    details: bytes = Column("details", LargeBinary)

    def asdict(self):
        raise NotImplementedError()

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
    @staticmethod
    def get_db_table():
        return _Entity
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
    @classmethod
    def get_entity_type(cls):
        return EntityType.Block
    def extract_record_values(self):
        return {
            'type': self.get_entity_type(),
            'subtype': self.__class__.__name__,
            'parent': getattr(self, 'parent', None),
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
            'order': self.order
        }

class ARelationship(ABlock):
    def extract_record_values(self):
        return {
            'type': EntityType.Relationship,
            'subtype':       self.__class__.__name__,
            'parent': None,
            'order': self.order
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

@dataclass
class ARepresentation(AWrapper):
    Id: Optional[int] = None
    diagram: Optional[int] = None
    styling: str = ""
    category: ReprCategory = ReprCategory.no_repr
    order: int = 0,

    @staticmethod
    def get_db_table():
        return _Representation

    def _to_db(self, **kwargs) -> Dict[str, Any]:
        return dict(
            Id=self.Id,
            diagram=self.diagram,
            category=self.category,
            subtype=type(self).__name__,
            **kwargs
        )

@dataclass
class _BlockRepresentation(ARepresentation):
    block: Optional[int] = None
    parent: Optional[int] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    category: ReprCategory = ReprCategory.block
    lane_length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    order: int = 0
    orientation: int = 0

    def extract_record_values(self) -> Dict[str, Any]:
        return self._to_db(
            entity=self.block,
            parent=self.parent,
            order=self.order,
        )

@dataclass
class _InstanceRepresentation(ARepresentation):
    category: ReprCategory = ReprCategory.block_instance
    block: Optional[int] = None
    parent: Optional[int] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    lane_length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    order: int = 0
    orientation: int = 0
    parameters: str = ''
    instance_role: str = ''

    def extract_record_values(self) -> Dict[str, Any]:
        return self._to_db(
            entity=self.block,
            parent=self.parent,
            order=self.order,
        )

@dataclass
class _MessageRepresentation(ARepresentation):
    message: Optional[int] = None
    parent: Optional[int] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    category: ReprCategory = ReprCategory.message
    order: int = 0
    orientation: float = 0.0
    direction: int = 0

    def extract_record_values(self) -> Dict[str, Any]:
        return self._to_db(
            entity=self.message,
            parent=self.parent,
            order=self.order
        )

@dataclass
class _RelationshipRepresentation(ARepresentation):
    relationship: Optional[int] = None
    source_repr_id: Optional[int] = None
    target_repr_id: Optional[int] = None
    routing: str = ''  # JSON list of Co-ordinates of nodes
    z: float = 0.0  # For ensuring the line goes over the right blocks.
    category: ReprCategory = ReprCategory.relationship
    anchor_offsets: str = ""
    anchor_sizes: str = ""

    def extract_record_values(self) -> Dict[str, Any]:
        return self._to_db(
            entity=self.relationship,
            link1=self.source_repr_id,
            link2=self.target_repr_id,
        )

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