





## Features for editing blocks

* Adding, deleting
* Moving, resizing
* Setting texts
* Anchoring texts
* Managing children (ports, texts)
* Setting styling for block
* Setting styling for children
* Providing default styling

## Features for editing connections

* Connecting blocks
* Adding waypoints
* Manipulating waypoints
* Anchoring children
* Setting texts
* Adding, deleting, moving messages (which are children)


# Implemented Mechanisms

1. Composite Pattern for both blocks and connections
2. Styling Mechanism
3. Asking for an anchor coordinate
4. Interacting with a data source
    * styling
    * position, size, waypoints
    * texts
    * children: tuple(anchor, type, data)
5. Marshalling
6. Sending triggers (events) when something has changed
7. Highlighting a selection
8. Decorating with editing handles