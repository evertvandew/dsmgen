// Run me with `qml diagram_editor.qml`.
// Requires QML 6.

import QtQuick 2.9;
import QtQuick.Controls 2.2;
import QtQuick.Shapes 1.12
import QtQml.StateMachine 6.0


ApplicationWindow {
    id: main_window
    visible: true; width: 640; height: 480;
    
    QtObject{
        id: internals
        property bool connectMode: true;
    }
    
    signal blockClicked(index: int)
    signal connectionClicked(index: int)
    
    
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
            onClicked: (mouse) => {
                blocks.append({"x": mouse.x, "y": mouse.y, "shape_type": 5});
            }
        }

        Repeater{
            id: blocks_view
            model: blocks
            Block{
                x: model.x
                y: model.y
                shape_type: model.shape_type
                
                onClicked: (index, mouse) => {
                    console.log("Clicked: "+index + mouse)
                    console.log("Current state:"+stateMachine.state)
                    main_window.blockClicked(index)
                }
            }
        }
        
        Repeater{
            id: connections_view
            model: connections

        }
    }
    
    
    
    StateMachine {
        id: stateMachine
        initialState: block_mode
        running: true        
        
        State {
            id: block_mode
            
            SignalTransition {
                targetState: connection_mode
                signal: editing_mode_btn.clicked
            }
            
            SignalTransition {
                signal: blockClicked
                onTriggered: (index) => {
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
            
            onEntered: {
                console.log("block editing mode")
                editing_mode_btn.text= "Edit drawing"
            }

            onExited: {
            }
        }
        
        State {
            id: connection_mode
            SignalTransition {
                targetState: block_mode
                signal: editing_mode_btn.clicked
            }
            onEntered: {
                editing_mode_btn.text= "Connect blocks"
                onBlockClicked: {
                    console.log("block " + index + " was clicked")
                }
            }
        }
    }
    
    
    Column {
        anchors.bottom: parent.bottom;
        anchors.right: parent.right;
        Button {
            id: editing_mode_btn
        }   // Button
    }
}
