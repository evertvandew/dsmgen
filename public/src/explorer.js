

RestData = function (cb) {
    let self = this;
    self.cb = cb;
}
RestData.prototype.get = function(id) {
    return this.lut[id];
}
RestData.prototype.get_all = function() {
    return this.data;
}
RestData.prototype.add = function(record) {
    let self = this;
}
RestData.prototype.update = function(record) {
    let original = this.lut[record.id];
    this.lut[record.id] = record;
    let index = this.data.indexOf(original);
    this.data[index] = record;
}
RestData.prototype.delete = function(record) {
    let original = this.lut[record.id];
    let index = this.data.indexOf(original);
    delete this.lut[record.id];
    delete this.data[index];
    if (record.parent) {
        let parent = this.lut[record.parent];
        let pindex = parent.children.indexOf(original);
        delete parent[pindex];
    }
}



function onEditClick(i) {
    let original = this.textContent;
    let wrapper = this;
    let input = document.createElement("INPUT");
    this.innerHTML = "";
    input.value = original;
    this.appendChild(input);
    $( this ).off("click");
    input.focus();
    input.onfocusout = function() {
        wrapper.innerHTML = input.value;
        if (input.value != original) {
            $(wrapper).trigger("input_changed");
        }
        $(wrapper).on("click", onEditClick);
    };
    $(wrapper).trigger("selected");
}

function addHierarchy(data) {
    /* extend the received (flat) records, and add hierarchy.
       This is done by adding the "children" attribute to objects,
       which are arrays containing the children objects.
       This adds circular references in the data that may make it
       harder to recycle the memory...
    */

    let origins = new Array();
    // First prepare a lookup table and reset the children
    let lookup = new Object();
    data.forEach(function(item, index) {
        lookup[item.id] = item;
        item.children = new Array();
    });
    // Now construct the hierarchy
    data.forEach(function(item, index) {
        // If the parent does not exist, orphan the item
        if (item.parent && !(item.parent in lookup)) {
            item.parent = null;
        }
        if (item.parent) {
            let parent = lookup[item.parent];
            parent.children.push(item);
        } else {
            origins.push(item);
        }
    });
    return origins;
}

function createExplorer(id, datasource) {
    const viewer = document.getElementById(id);

    function loadData(data, parent) {
        /* create the DOM representations of the data */
        let is_root = parent == null;
        if (parent == null) {
            parent = $("#table_editor")[0];
            // Clear away all elements in the editor.
            while (parent.firstChild) {
                parent.removeChild(parent.firstChild);
            }
        }
        data.forEach(function(item, index) {
            let child_row = document.createElement("DIV");
            child_row.className = "level input_row";
            child_row.id = "input_row_" + item.id;
            let col = null;
            let actions = document.createElement("DIV");
            actions.className = "action";
            msg = '<i class="fa fa-plus-square actbut" data-action="add"></i>';
            if (!is_root) {
                msg += ' <i class="fa fa-caret-square-left actbut" data-action="promote"></i>';
            }
            if (index > 0) {
                msg += ' <i class="fa fa-caret-square-right actbut" data-action="demote"></i>';
                msg += ' <i class="fa fa-caret-square-up actbut" data-action="up"></i>';
            }
            if (index < data.length-1) {
                msg += ' <i class="fa fa-caret-square-down actbut" data-action="down"></i>';
            }
            if (!item.children.length) {
                msg += ' <i class="fa fa-times actbut-del" data-action="delete"></i>';
            }
            actions.innerHTML = msg;
            child_row.appendChild(actions);

            loadData(item.children, child_row);
            parent.append(child_row);
            $(child_row).addEventListener("change", function(e) {
                e.stopPropagation();
                results = {'id': item.id};
                % for i, key in enumerate(columns):
                    results.${key} = child_row.children[${i}].innerHTML;
                % endfor
                all_data.update(results);
            });
            $(child_row).on("selected", function(e) {
                e.stopPropagation();
                setSelected(item.id);
            });
        });

        // After handling all elements, subscribe to some events
        if (is_root) {
            $(".edit").click(onEditClick);
            $(".actbut").click(onAction);
            $(".actbut-del").click(onAction);
        }
    }


    function onAction(e) {
        e.stopPropagation();
        // Determine which button was pressed, and on which element
        let row = this.parentElement.parentElement;
        // Find the hidden input that contains the object id.
        let obj_id = row.id.slice(10);
        let record = all_data.get(obj_id);
        let action = this.getAttribute("data-action");
        if (action == 'add') {
            // Create a new object
            let new_object = {"parent": record ? record.id : null,
                            "children": []};
            all_data.add(new_object);
        } else if (action == 'delete') {
            event.stopPropagation();
            $("#ackDeleteYes").on('click', function() {
                all_data.delete(record);
                $("#ackDelete").modal('hide');
                refresh();
                let event = new Event("element_delete", { bubbles: true, cancelable: false, proc_id: record.id});
                row.dispatchEvent(event);
            });
            $("#ackDelete").modal('show');
        } else if (action == 'demote') {
            // Find the record above this one and make it its parent.
            if (!record.parent) {
                let my_index = hierarchy.findIndex((o) => o.id == record.id);
                var new_parent = hierarchy[my_index-1];
                new_parent = new_parent.id;
            } else {
                let parent = all_data.get(record.parent);
                let my_index = parent.children.indexOf(record);
                var new_parent = parent.children[my_index-1].id;
            }
            record.parent = new_parent;
            all_data.update(record);
        } else if (action == 'promote') {
            // Find the record above this one and make it its parent.
            let parent = all_data.get(record.parent);
            record.parent = parent.parent;
            all_data.update(record);
        } else if (action == "up") {
            let other = null;
            if (!record.parent) {
                let my_index = hierarchy.findIndex((o) => o.id == record.id);
                other = hierarchy[my_index-1];
            } else {
                let parent = all_data.get(record.parent);
                let my_index = parent.children.indexOf(record);
                other = parent.children[my_index-1];
            }
            // Swap my number with the one of the previous one; built-in sorting will do the rest.
            let tmp = record.${count_col};
            record.${count_col} = other.${count_col};
            other.${count_col} = tmp;
            all_data.update(record);
            all_data.update(other);
        } else if (action == "down") {
            let other = null;
            if (!record.parent) {
                let my_index = hierarchy.findIndex((o) => o.id == record.id);
                other = hierarchy[my_index+1];
            } else {
                let parent = all_data.get(record.parent);
                let my_index = parent.children.indexOf(record);
                other = parent.children[my_index+1];
            }
            // Swap my number with the one of the previous one; built-in sorting will do the rest.
            let tmp = record.${count_col};
            record.${count_col} = other.${count_col};
            other.${count_col} = tmp;
            all_data.update(record);
            all_data.update(other);
        }
        // With an ADD, we must wait until the reply from the server is handled.
        // That reply contains the ID of the new object which we need to process
        // the data structures. So, ADD is handled in a callback instead of below.
        // DELETE is handled in the callback of the Acknowledgement.
        if (action != 'add' && action != 'delete') {
            refresh();
        }
    }

    function resetHierarchyNumbers(h, parent=null) {
        /* Each element in the hierarchy h is re-numbered according to their
           place in the hierarchy.
         */
        let prefix = (parent) ? parent.${count_col} + '.' : '';
        for (var i=0; i<h.length; i++) {
            let item = h[i];
            // First determine the number for the direct children
            if (parent) {
                let number = prefix + (i+1);
                if (number != item.${count_col}) {
                    item.${count_col} = number;
                    all_data.update(item);
                }
            }
            // Then descend into the children, recursively.
            resetHierarchyNumbers(item.children, item);
        }
        return h;
    }

    function refresh() {
        // Determine the hierarchy initially and when handling ADD.
        // We use a global variable, hierarchy.
        hierarchy = resetHierarchyNumbers(addHierarchy(all_data.get_all()));

        // Construct the elements while initially loading and when handling ADD.
        loadData(hierarchy);
    }


    let data = datasource.get_all();
    // First add hierarchical details
    let all_data = addHierarchy(data);
    loadData(all_data, null);
}
