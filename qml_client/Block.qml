import QtQuick 2.15
import QtQuick.Shapes 1.0;

Item {
    id: block
    signal clicked(index: int)

    width: 40; height: 25

    Rectangle {
        id: rectangle
        border.color: "black"
        color: "yellow"
        anchors.fill: parent

        MouseArea {
            anchors.fill: parent
            propagateComposedEvents: false
            onClicked: {
                block.state = "HIGHLIGHTED";
                block.clicked(index)
            }
        }
        
        ListModel{
            id: handles
        }
        
        Repeater{
            id: resize_handles
            model: handles
            Handle{
                x: model.x
                y: model.y
                onDragged: {
                    if (index == 0 || index == 3) {
                        block.x = block.x + newX
                        block.width = block.width - model.x
                        resize_handles.itemAt(index).x = 0
                    } else {
                        block.width = block.width + newX - model.x
                    }
                    if (index == 0 || index == 1) {
                        block.y = block.y + newY
                        block.height = block.height - model.y
                        resize_handles.itemAt(index).y = 0
                    } else {
                        block.height = block.height + newY - model.y
                    }
                    model.x = newX
                    model.y = newY
                    for (var i=0; i<4; i++) {
                        var h = resize_handles.itemAt(i);

                        if (i==0) {
                            h.x = 0
                            h.y = 0
                        } else if (i==1) {
                            h.x = block.width-10
                            h.y = 0
                        } else if (i==2) {
                            h.x = block.width-10
                            h.y = block.height-10
                        } else if (i=3) {
                            h.x = 0
                            h.y = block.height-10
                        }
                    }
                }
            }
        }
    }
    
    function decorate() {
        handles.clear()
        handles.append({x:0, y:0})
        handles.append({x:width-10, y:0}),
        handles.append({x:width-10, y:height-10}),
        handles.append({x:0, y:height-10})
    }
    
    states: [
        State {
            name: ""
            StateChangeScript { script: handles.clear() }
        },
        State {
            name: "HIGHLIGHTED"
            PropertyChanges { target: rectangle; border.color: "blue"; border.width: 3 }
            StateChangeScript { script: decorate() }
        },
        State {
            name: "DECORATED"
            PropertyChanges { target: rectangle; border.color: "lightblue" }
        }
    ]
    
}
 
