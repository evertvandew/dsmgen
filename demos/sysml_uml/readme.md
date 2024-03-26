

# SysML / UML modelling tool

## Getting started

To generate + run this tool, execute the `run.py` command.
This will install all the relevant files into a `build` directory,
and start a web server that is listening to port 5003. Just point a browser to 
[http://localhost:5003/sysml_uml_client.html] and start modelling.


## Supported UML diagrams

At the moment, the following diagrams are supported:

Structural Diagrams:
* Class Diagram
* Component Diagram
* Deployment Diagram
* Object Diagram
* Package Diagram

Behavioural Diagrams:
* Use Case Diagram
* Activity Diagram
* State Machine Diagram


At the moment, the following diagrams are _not_ supported:
* Composite Structure Diagram -- requires editing a network inside a block ("inner diagrams")
* Sequence Diagram -- requires a "laned" diagram
* Communication Diagram -- requires messages anchored on relationships
* Interaction Overview Diagram -- requires inner diagrams + lanes
* Timing Diagram -- very loosely defined, probably requires custom coding

## Supported SysML diagrams

SysML re-uses a lot of the UML diagrams & concepts, but it adds some:

* Block Definition Diagram
* Inner Block Definition Diagram
* Requirement Diagram
* Parametric Diagram


