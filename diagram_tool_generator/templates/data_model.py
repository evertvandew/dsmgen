<%
"""
    Template for generating the data model for the visual modelling environment.
    The data model will use the SQLAlchemy library.

"""

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
        'longstr': 'str'
    }.get(t, '')
    return tp or t

%>

from datetime import datetime, time
import json
from enum import IntEnum, auto
from contextlib import contextmanager
import logging
from dataclasses import dataclass, fields, asdict, field, is_dataclass
from sqlalchemy import (create_engine, Column, Integer, String, DateTime,
     ForeignKey, event, Time, Float, LargeBinary, Enum)
from sqlalchemy.orm import scoped_session, sessionmaker, backref, relationship
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("${config.dbase_url}")

Session = sessionmaker(engine)

Base = declarative_base()


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
    __tablename__ = 'version'
    Id = Column(Integer, primary_key = True)
    category =  Column(String)
    versionnr = Column(String)


def init_db():
    Base.metadata.create_all(bind=engine)
    with session_context() as session:
        if session.query(Version).count() < 2:
            session.add(Version(category="generator", versionnr="0.1"))
            session.add(Version(category="model", versionnr=${md.get_version()}))

        % if md.model_definition.initial_records:
        if session.query(_Entity).count() == 0:
            % for r in md.model_definition.initial_records:
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
    Diagram = auto()
    LogicalElement = auto()
    Port = auto()

class _Entity(Base):
    __tablename__ = '_entity'

    Id = Column(Integer, primary_key=True)
    type = Column(Enum(EntityType))
    subtype = Column(String)
    parent = Column(Integer, ForeignKey("_entity.Id"))  # For subblocks and ports
    order = Column(Integer)
    details = Column("details", LargeBinary)

class _Relationship(Base):
    __tablename__ = '_relationship'

    Id = Column(Integer, primary_key=True)
    subtype = Column(String)
    source_id  = Column(Integer, ForeignKey("_entity.Id"))
    target_id  = Column(Integer, ForeignKey("_entity.Id"))
    associate_id = Column(Integer, ForeignKey("_entity.Id"))
    details = Column("details", LargeBinary)

class _BlockRepresentation(Base):
    __tablename__ = '_block_representation'

    Id = Column(Integer, primary_key=True)
    diagram = Column(Integer, ForeignKey("_entity.Id"))
    block = Column(Integer, ForeignKey("_entity.Id"))
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)   # For placing blocks etc on top of each other
    styling = Column(String)

class _RelationshipRepresentation(Base):
    __tablename__ = "_relationship_representation"

    Id = Column(Integer, primary_key=True)
    diagram = Column(Integer, ForeignKey("_entity.Id"))
    relationship = Column(Integer, ForeignKey("_relationship.Id"))
    routing = Column(LargeBinary)       # JSON list of Co-ordinates of nodes
    z = Column(Float)                   # For ensuring the line goes over the right blocks.
    styling = Column(String)


# ##############################################################################
# # Helper for serializing classes.
# # For deserializing, all elements must consume the json in the constructor.

class ExtendibleJsonEncoder(json.JSONEncoder):
    def default(self, o):
        """ We have three tricks to jsonify objects that are not normally supported by JSON.
            * Dataclass instances are serialised as dicts.
            * For objects that define a __json__ method, that method is called for serialisation.
            * For other objects, the str() protocol is used, i.e. the __str__ method is called.
        """
        if hasattr(o, '__json__'):
            return o.__json__()
        if is_dataclass(o):
            result = asdict(o)
            result['__classname__'] = type(o).__name__
            return result
        return str(o)


# ##############################################################################
# # Custom data classes for handling the custom modelling entities.


class WrongType(RuntimeError): pass


class longstr(str): pass

class AWrapper:
    def store(self, session=None):
        if session is None:
            with session_context() as session:
                self.store(session)
        else:
            if self.id:
                self.update()

            data_bytes = self.asjson()
            table = self.get_db_table()
            # See if there already is a record for this item.
            record = table(**self.extract_record_values(), details=data_bytes)
            session.add(record)
            session.commit()        # Intermediate commit to determine the ID
            # Update the original data with ID the record got from the dbase.
            self.id = record.Id
            data_bytes = self.asjson()
            record.details = data_bytes

    def asjson(self):
        return json.dumps(self, cls=ExtendibleJsonEncoder).encode('utf8')

    @classmethod
    def retrieve(cls, id):
        with session_context() as session:
            record = session.query(cls.get_db_table()).filter_by(Id=id).first()
            if record.subtype != cls.__name__:
                raise WrongType()
            data_dict = json.loads(record.details.decode('utf8'))
            return cls(**data_dict)

    def update(self):
        with session_context() as session:
            record = session.query(self.get_db_table()).filter_by(Id=self.id).first()
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
        data_dict = json.loads(record.details.decode('utf8'))
        assert typename == data_dict['__classname__']
        data_dict = {k:v for k,v in data_dict.items() if k != '__classname__'}
        return cls(**data_dict)

@dataclass
class ABlock(AWrapper):
    order: int = 0
    @staticmethod
    def get_db_table():
        return _Entity
    def extract_record_values(self):
        return {
            'type': EntityType.Block,
            'subtype': self.__class__.__name__,
            'parent': self.parent if hasattr(self, 'parent') else None,
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
class APort(ABlock): pass

class ADiagram(ABlock): pass

class ALogicalElement(ABlock): pass

# Generated dataclasses

% for entity in generator.ordered_items:
<%
    stereotype = 'ABlock' if entity in generator.md.entity else \
                 'ARelationship' if entity in generator.md.relationship else \
                 'APort' if entity in generator.md.port else \
                 'ALogicalElement' if entity in generator.md.logical_model else \
                 'ADiagram'
%>
@dataclass
class ${entity.__name__}(${stereotype}):
    Id: int = 0
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${get_type(f.type)} = ${generator.get_default(f.type)}
    % endfor

% endfor

if __name__ == '__main__':
    init_db()