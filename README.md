





# Plan for this tool

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









# Running the tool



For more information please visit http://brython.info.