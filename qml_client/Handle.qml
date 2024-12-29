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
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        drag.target: parent
        propagateComposedEvents: false
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
