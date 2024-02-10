# Block programming demo

This examples allowes programs to be constructed by connecting pre-defined blocks.
Blocks have ports that can be connected. Ports come in two flavours: synchronous and asynchronous.
For each port type, there is an input version and an output. Ports can not be both input and output.

## Synchronous vs Asynchronous ports
A key design decision in block-oriented software is to determine when each output fires an event.
In this design, the assumption is that an output produces one and only one event when a single event has been
received on all of its inputs. This is called _synchronous_ communication, and is how the synchronous inputs
and outputs work.

The code that is generated from a model should check if any input receives more events than the other inputs,
that would be an error that could lead to serious unpredictable behaviour.

However, in many systems there is also the need to `asynchrnous` events. These operate independently from the
other inputs and outputs. Often they are used to modify the state of a system in response to e.g. a user action.

An asynchronous input event _can_ trigger an asynchronous output event, but it must NEVER generate a synchronous
output event.

The modelling tool will not allow connections between an asynchronous port and a synchronous port.

## Hierarchy
It supports hierarchy using the `SubProgram` block.
Double-clicking on this block opens a new diagram (in a tab) for editing the inner diagram.

Inside the inner diagram new ports can be created. They are represented using labels.

## Library
Block in the library can be defined in two ways: using a block with an explicit implementation in code,
or a `SubProgramDefinition`. Both can have parameters, whenever a library block is used, either in a
program or a `SubProgramDefinition`, those parameters need to be given values.

Blocks can be inserted in a diagram by dragging them from the model explorer (on the left) into the diagram.


# Code generation
Code generation is not supplied in the demo, but can be added by the user.

The model is stored in an SQLite3 database. A datamodel is generated in `built/block_programming_data.py`.
It uses `sqlalchemy`. This can be used to interact with the database.

# Where is the python source for the client?
The server serves the python source files from either the `public` directory, or, if it is not there,
from the `graphs/client_src` directory. This is to keep a single version of that code.

