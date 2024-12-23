import QtQuick 2.15
import QtQuick.Shapes 1.12

Item {
    id: handle
    signal dragged(newX: int, newY: int)

    width: 10; height: 10

    Rectangle {
        id: rectangle
        anchors.fill: parent
        color: "#29B6F2"

        // MouseArea {
        //     anchors.fill: parent
        //     propagateComposedEvents: false
        //     onClicked: {
        //         console.log("Handle clicked")
        //     }
        // }
        //Drag.onDragMove: console.log("move")
    }

    // Shape {
    //     ShapePath {
    //         strokeWidth: 0
    //         //strokeColor: "transparent"
    //         strokeColor: "black"
    //         fillColor: "#29B6F2"
    //         startX: 0
    //         startY: 0
    //         PathSvg {
    //             path: "a "+radius+" "+radius+" 0 0 1 "+2*radius+" 0 a "+radius+" "+radius+" 0 0 1 -"+2*radius+" 0 z"
    //         }
    //         //PathSvg { path: "a 5 5 0 0 1 10 0 a 5 5 0 0 1 -10 0 z" }
    //     }
    // 
    // }


    MouseArea {
        id: mouseArea
        anchors.fill: parent
        drag.target: parent
        propagateComposedEvents: false
        //onPressed: console.log("Handle pressed")
        onClicked: console.log("Handle clicked")
        onMouseXChanged: {
            if (drag.active) {
                handle.dragged(parent.x, parent.y)
            }
        }
        onMouseYChanged: {
            if (drag.active) {
                handle.dragged(parent.x, parent.y)
            }
        }
        drag.threshold: 0
    }
}
