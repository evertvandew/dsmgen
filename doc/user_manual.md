# Starting the generated Modeling Tool

RIGHT NOW, THE SOFTWARE ASSUMES YOU ARE USING A LINUX COMPUTER.

The software currently uses soft-links to share files between instances.
That will not be very difficult to change, but I don't have a windows computer to test it on, so I will not attempt it.

## Installing pre-requisites

This software requires a Python 3.11+ interpreter, with the necessary dependencies installed.
Dependencies can be installed using PIP, by running the following command in the root directory of this project:

```commandline
python -m pip install -r requirements.txt
```

There are a number of JavaScript modules this tool depends on. 
These are pre-downloaded in the `/public` directory of this project.
As this project matures, a JS package manager should be used instead.

## Running the tool

To run the modeling tool, three steps must be taken:
* Code must be generated from the specification file.
* Other resources must be copied or linked to the right location.
* The server must be started.

The demos have a `run.py` file that performs all three steps, running the server on your local PC.

When the server is started, it will report which port it is listening on. This information is needed to use the client.
For example, the sysml_uml demo reports as the final line:

```commandline
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5103
 * Running on http://192.168.178.107:5103
Press CTRL+C to quit
```

Either of the URLs reported by the server can be used to open the client in a browser.
Instead of the `127.0.0.1` loopback IP address, one can use `http://localhost:5103`

# Using the generated Modeling Tool

![Example diagram][/doc/example_diagram.png]

The generated modeling tool will present the user with a screen with three parts: 
* The *model explorer* at the left.
* The *diagram editor* at the top right.
* The *details editor* at the bottom right. Clicking on any item in either the explorer or the diagram editor will have
  the details of this item displayed in the details editor.

## Filling a Model

Initially, a model will have only the initial elements as detailed in the specification file. 
These elements will only be shown in the explorer on the left.
By right-clicking on any of these items, existing items can be deleted or new items created.
New items are placed in the explorer as child of the item that was right-clicked.

![Context Menu for a Functional Model][/doc/explorer_right_click.png]

As showing in the image above, there is a limited number of items that can be created from each item. 
This helps a model maintain a logical structure.
Which elements can be created as children is detailed in the model specification.

In order to create a diagram that can be visually edited in the diagram editor, a diagram item needs to be created first.
In the example above, two diagrams can be created: a CommunicationDiagram and a UseCaseDiagram.
After selecting the type of item to create, a pop-up dialog is displayed to set the attributes of this item.

Once a diagram is created, double-clicking on it will open that diagram in the diagram editor. 

<xxxxx diagram van Use Case>

In the left edge of the diagram editor, a column of buttons is shown that will create new blocks.
These blocks will appear at a fixed location in the diagram, and can be dragged to where the User wants it to be.

## Adding Relationships
Once two or more blocks have been created, they can be connected. For this, click the connect button ![Connect Button](/doc/connect_btn.png).
Then, first click the "source" item, and then the "target" item.

When the target block is clicked, the constraints for that connection are checked by the client.
It will determine if there are zero, one or many possible relationships between the source and the target.
If there are multiple, the user will be asked to select one from a list.
If there are none, the user will be given an error message.
If there is only one, the relationship will be established without further user input.

Which block is the source and which is the target does make a difference.
So if a connection can not be made, sometimes one needs to click the other block first.

## Using one element in multiple diagrams

It is possible to re-use an element in several diagrams, simply by dragging an existing item from the explorer
into a diagram.

## Adding Ports

Some block are allowed to have ports (connection points).
There are two ways to manage these ports:
* The properties editor for the block, using the '+' button shown below.
* Using the right-click context menu in the explorer.

<xxxxxxx port editor window>

(Whether a block can have ports, is determined in the model specification)

## Compound blocks

Some blocks (compound blocks) are diagrams that can also be placed in diagrams. 
They allow hierarchy in a diagram. By double-clicking on these blocks, the associated diagram is opened.

If these blocks are allowed to have ports, these ports are represented as labels that can be created using the
buttons at the left of the diagram, like any block.

<xxxxxx Block labels in a compound block>

## Deleting elements

In the diagram editor, the currently selected item can be deleted by pressing the "delete" key.
In the explorer, items can be deleted using the right-click context menu.
Some items can be deleted in the details editor, like the ports associated with a block.

Currently, there is no way to undo or redo any changes.
This will be added in the future, but for now, "You Asked For It, You Got It" applies.

If an item is deleted that has other elements dependent on it, they are all deleted without informing the user.
This includes representations in diagrams, ports, children and connections (and their respective representations).

I guess implementing an undo mechanism is a pretty high priority 😉
