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
    
    property int block_a
    property int block_b
    
    
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
                blocks.append({
                    "x": mouse.x,
                    "y": mouse.y,
                    "width": 100,
                    "height": 40,
                    "shape_type": 5});
            }
        }

        Repeater{
            id: blocks_view
            model: blocks
            Block{
                x: model.x
                y: model.y
                width: model.width
                height: model.height
                shape_type: model.shape_type
                
                onClicked: (index, mouse) => {
                    main_window.blockClicked(index)
                }
            }
        }
        
        Repeater{
            id: connections_view
            model: connections
            Connection {
                a_details: blocks_view.itemAt(model.block_a)
                b_details: blocks_view.itemAt(model.block_b)
            }
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
                editing_mode_btn.text= "Connect blocks"
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
            SignalTransition {
                targetState: block_a_selected
                signal: blockClicked
                onTriggered: (index) => {
                    console.log("A block " + index + " was clicked")
                    block_a = index
                }
            }
            onEntered: {
                editing_mode_btn.text= "Edit drawing"
            }
        }
        
        State {
            id: block_a_selected
            SignalTransition {
                targetState: connection_mode
                signal: blockClicked
                onTriggered: (index) => {
                    console.log("B block " + index + " was clicked")
                    block_b = index
                    connections.append({"block_a": block_a, "block_b": block_b})
                    console.log('Created a connection:'+block_a+' '+block_b)
                    console.log('The blocks:'+blocks_view.itemAt(block_a)+' '+blocks_view.itemAt(block_b))
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
