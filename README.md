
# Welcome to the Domain Specific Model Generator (dsmgen)

![Example diagram][doc/example_diagram.png]

Block diagrams have proven to be the most valuable tool for gaining insight and understanding
in complex systems. They are the ubiquitous tools of software and systems engineers.

While standardized modeling tools have been created around UML and SySML, block diagrams are much more widely applicable.
And just like Domain Specific Languages have proven themselves in bridging the gap between domain specialists and
the IT world, Domain Specific Models are expected to be as or even more useful.

This tool generator was created to facilitate the building of Domain Specific Modeling Tools.
To use it, first define a description of the model structure. 
Then, this specification will be used to generate a database for storing the model with an REST API for accessing it,
and a web-client for editing the model.

![Basic workflow][doc/usage.png]

# Quickstart
For the curious / impatient, a number of demos have been created with predefined model specifications ready to run.
Each demo has a `run.py` file that can be run by a model Python 3 interpreter (after installing the necessary modules).
This will generate the database and client software, and run a server.

# Documentation

Documentation can be found in the `doc` directory.

* [Using the generated tool](doc/user_manual.md)
* Description of the [model specification](doc/specification_language.md)
* Running the [demos](demos/readme.md)

# Status & future plan for this tool

This software has the status of "Minimum Viable Product". It has enough features to be useful, 
but there are many rough edges and possible improvements. 

This tool is growing as experience is gained making various diagrams. The goal is to refactor it in such a way
that the diagram-specific details become part of the model specification, and the other code is a generic framework
for building a graphical modelling tool. At the moment, I do not have enough understanding of the problem space
(drawing various diagrams) to make a good design for this, so this design will have to emerge.

While the design is still crystalising / emerging, I intend to keep this codebase in Python. Due to the magic
of Brython, modern Python 3 is (almost) fully supported in the browser.
When the design is sufficiently solid, it should probably be ported to a language that is easier to maintain 
(i.e. where a compiler helps keeping the code consistent).
That language may be Typescript, though I'd prefer a better language.
Perhaps even Rust to generate WASM, and use `wasm_bindgen` to connect to the DOM API. I love Rust.
As the intelligent part of the tool is in a code generator, it will be relatively easy to port to another language.

For more information about Brython please visit http://brython.info.

# Copyright & License

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
