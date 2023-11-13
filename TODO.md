
# Bugs:
* When "delete" is pressed while editing a property, the block is deleted. The "focus" is not taken into account.



# TODO for the First Viable Product Release:
* Add shape for Document
* Support multiple document types
* Support for container blocks
  * Limiting the position of internal waypoints to within the container
  * Dynamically create and remove ports as connections crossing the boundary are changed.
* Allow conversion of one type element to another
* Allow conversion of one relationship to another
* Make auto-save work for simple file interface
* Interact with a tree view of the model
* Support wide open lines
* Support curved lines
* Support scrolling of the diagram
* Edit the styling of lines.
* Button for copying styling from object to object(s)
* Support styling multiple objects at once
* Make a collection of diagrams, supporting at least UML and SYSML.

# Future enhancements
* Implement a proper Z-order in the diagrams.
* The explorer should handle create and rename events from entities created while editing a diagram.
* Port to an environment where the javascript is pre-compiled. Probably pyjamas or pyjaco?
* Add in-diagram buttons for the different editing modes.
* Automatisch uitlijnen en grootte van blokken bepalen.



# Done:
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

