import QtQuick 2.9;
import QtQuick.Controls 2.2;
import QtQuick.Shapes 1.0;


ApplicationWindow {
    visible: true; width: 640; height: 480;
    QtObject{
        id: internals
        property bool connectMode: true;
    }
    
    
    Rectangle {
        id: page
        width: 320; height: 480
        color: "white"
        
        ListModel{
            id: blocks
 //           ListElement{ x: 100; y: 100}
        }
        ListModel{
            id: connections
        }
        ListModel{
            id: messages
        }
              
        MouseArea{
            anchors.fill: parent
            onClicked: {
                blocks.append({"x": mouse.x, "y": mouse.y});
            }
        }

        Repeater{
            id: blocks_view
            model: blocks
            Block{
                x: model.x
                y: model.y
                onClicked: {
                    console.log("block " + index + " was clicked")
                    for (var i = 0; i<blocks_view.count; i++) {
                        if (i == index) {
                            blocks_view.itemAt(i).state = "DECORATED";
                        } else {
                            blocks_view.itemAt(i).state = "";
                        }
                    }
                }
            }
        }
    }
    
    
    Column {
        anchors.bottom: parent.bottom;
        anchors.right: parent.right;
        Button {
            text: internals.connectMode ? "Edit drawing" : "Connect blocks";
            onClicked: internals.connectMode = !internals.connectMode;
        }   // Button
    }
    
}
