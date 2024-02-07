

# Bugs:
* When editing the name of a block or adding one, the explorer is not updated.
* When "delete" is pressed while editing a property, the block is deleted. The "focus" is not taken into account.
* Some exceptions occur when manipulating connections.
* Use `get_type_hints` instead of raw `__annotations__`.
* Double-click on a subprogram doesn't open the associated diagram.
* When dragging an object, escape does not stop the behaviour if the mouse is not pressed down.


# TODO for the First Viable Product Release:
* Make a demo of the block_programming model.
* Make a collection of diagrams, supporting at least UML and SYSML.
  - For now, except the sequence diagram because it requires laneing support.

# Refactoring
* Make parts in the model definition that are used in generating the tool, parts of the decorator call
  instead of the dataclass part.
* Check if the various entities in the model_definition still need to be dataclasses.

# Future enhancements
* Make transactions of what happens in an event handler, so that if an exception occurs, the system stays in a known 
  state.
* Allow extra details to be shown around a relationship.
* When a user adds a connection that already exists, that should be reused.
* Allow conversion of one type element to another
* Allow conversion of one relationship to another
* Support for "laned" diagrams (sequence diagrams, gantt charts)
* Support for "puzzle" plug-in diagrams (scratch, Nassi–Shneiderman)
* Support for container blocks
  * Limiting the position of internal waypoints to within the container
  * Dynamically create and remove ports as connections crossing the boundary are changed.
  * Support for tabbed containers (LabVIEW)
* Allow styling of ports
* Let e.g. directionality of a port affect its rendering
* Support styling multiple objects at once
* Button for copying styling from object to object(s)
* Support wide open lines
* Support curved lines
* Add support for association classes (a third association with a relationship)
* Add support for messages along connections.
* Allow combinations of point-2-point routed and square routed connections.
* Implement a proper Z-order in the diagrams.
* The explorer should handle create and rename events from entities created while editing a diagram.
* Port to an environment where the javascript is pre-compiled. Probably pyjamas or pyjaco? Or perhaps to Kotlin?
* Automatisch uitlijnen en grootte van blokken bepalen.
* Scrolling of the diagram viewer.
* Resizing of the frames in the tool (explorer / diagram / details).
* Implementation of Undo / Redo.
* Implement the data model using Prisma (https://eash98.medium.com/why-sqlalchemy-should-no-longer-be-your-orm-of-choice-for-python-projects-b823179fd2fb)



# Done:
* Support managing multiple diagrams using tabs.
* Edit the styling of lines.
* When a user deletes the last representation of a connection, the underlying connection must be deleted.
* Interact with a tree view of the model
* Refactor the client-side serialization to put more logic in the data classes, not the RestApi.
* Add shape for Document
* Support multiple document types
* Support storage in an SQLite database over a REST API.
* Edit the styling of objects.
* Refactor for the locations of the source files
* Allow styling of different model elements
* Support for container blocks
  * Detect adding and removing blocks to the container
    * Adding by dragging blocks inside the container
    * Removing by dragging blocks outside the container
  * Limit the size of the container to the extent of its children & their relationships
  * When objects are added to a group, they must be ordered above the group.
  * When deleting an object inside a group, delete its relationships.
* Feature support for ports:
  - When dropping a block with ports, also drop representations for the ports
  - When loading a diagram, also load the associated ports
  - Store the Orientation in the styling for a port. Also useful for dedicated input & output ports.
  - Generate Port representations
  - Generate a list of allowed ports for each block
  - Generate blocks with ports a special variable to contain them
  - Add a PortRepresentation to the database model
  - In the client, treat ports as sub-blocks when persisting new or updated blocks
* Replace the REST "API" stuff with simple forwarding scheme. Letting objects maintain their own dirty state is a bad idea.
  Use a more centralized approach where actions are detected and lead to centralized sequences being run to handle the change.

