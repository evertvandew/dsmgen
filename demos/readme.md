# Modeling Tool Generation demos

Here are a number of demos to show some of the possibilities of the Modeling Tool Generator.

## Prerequisites

On Linux:
* Python3.11+ needs to be installed.
* Create a virtualenv for this project and activate it
  * python3.x -m venv venv
  * source venv/bin/activate
* Install the dependencies for this project into the virtual environment using `pip`:
  * python -m pip install -r requirements.txt

## Running the demos

Each demo has a file to automatically generate the tool and run it in a simple server.
`cd` to the desired directory, and simply run `python run.py`.

Each demo runs at a different port:
* Block programming: port 5101
* Model modeling: port 5102
* UML/SySML modeling (partial support): port 5103

The exact URL to use for opening the tool is given in a readme file in each demo. 
These readme files also give a description of the specific tool and some user documentation.
