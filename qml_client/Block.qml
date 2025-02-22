import QtQuick 2.15
import QtQuick.Shapes 1.12

Item {
    
    enum ShapeType {
        Rect,
        Square,
        Circle,
        Ellipse,
        Note,
        Component,
        Diamond,
        Folder,
        Closed_circle,
        Transparent_circle,
        Ringed_closed_circle,
        Bar,
        Hexagon,
        Octagon,
        Box,
        Drum,
        Stickman,
        Oblique_rect,
        Tunnel,
        Document,
        Tape,
        Triangle_down,
        Triangle_up,
        Hourglass,
        Label,
        Cloud
    }
    
    function getShapePath(shape_type : int, width: int, height: int) : string {
        switch(shape_type) {
            case 1:
                return "M 0 0 h %0 v %1 h -%0 z".arg(width).arg(height);
            case 2:
                return "M 0 0 h %0 v %0 h -%0 z".arg((width+height)/2);
            case 3:
                // arg0: radius. arg1: diameter
                return "M 0,%0 a %0,%0 0 0 0 %1,0 a %0,%0 0 0 0 -%1,0".arg((width+height)/4).arg((width+height)/2);
            case 4:
                return "M 0,%1 a %0,%1 0 0 0 %2,0 a %0,%1 0 0 0 -%2,0".arg(width/2).arg(height/2).arg(width);
            case 5:
                return "M %0,%2 l -%2,-%2 v %2 Z M %0,%2 V %1 H 0 V 0 h %3 z"
                .arg(width).arg(height).arg(0.1*width).arg(0.9*width);
        }
    }
    
    
    id: block
    signal clicked(index: int)

    width: 40; height: 25;
    property var drag_start: Qt.point(0,0);
    property int shape_type: 5;
    

    Rectangle {
        id: rectangle
        anchors.fill: parent
        
        ListModel{
            id: handles
        }
        
        // BlockShape {
        //     block: block
        // }
                
        Shape {
            id: shape
        
            ShapePath {
                fillColor: "yellow"
                strokeColor: "black"
                startX: 0; startY: 0
        
                PathSvg {
                    //path: "M 0 0 h "+block.width+" v "+(block.height)+" h -"+block.width+" z"
                    path: getShapePath(block.shape_type, block.width, block.height)
                }
            }
        }

        
        MouseArea {
            anchors.fill: parent
            propagateComposedEvents: false
            drag.target: parent
            drag.threshold: 0
            onClicked: {
                block.clicked(index)
            }
            onPressed: (mouse) => {
                block.state = "DRAGING";
                block.drag_start = Qt.point(mouse.x, mouse.y);
            }
            onMouseXChanged: (mouse) => {
                if (block.state == "DRAGING") {
                    block.x += mouse.x - block.drag_start.x;
                }
            }
            onMouseYChanged: (mouse) => {
                if (block.state == "DRAGING") {
                    block.y += mouse.y - block.drag_start.y;
                }
            }
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
    
    states: [
        State {
            name: ""
            StateChangeScript { script: handles.clear() }
        },
        State {
            name: "HIGHLIGHTED"
            PropertyChanges { target: rectangle; border.color: "blue"; border.width: 3 }
        },
        State {
            name: "DECORATED"
            PropertyChanges { target: rectangle; border.color: "lightblue" }
            StateChangeScript { script: decorate() }
        },
        State {
            name: "DRAGING"
            StateChangeScript { script: handles.clear() }
        }
    ]
    
    function decorate() {
        handles.clear()
        handles.append({x:0, y:0})
        handles.append({x:width-10, y:0}),
        handles.append({x:width-10, y:height-10}),
        handles.append({x:0, y:height-10})
    }
    
    function getSize() {
        return Qt.point(width, height)
    }
    function getCenter() {
        return Qt.point(x+width/2, y+height/2)
    }
    function copysign(a, b) {
        let aa = Math.abs(a)
        if (b < 0) {
            return -aa
        } else if (b > 0) {
            return aa
        }
        return 0
    }
    function intersect(b: Qt.point) {
        let halfsize = Qt.point(width/2, height/2)
        let a = getCenter()
        let delta = Qt.point(b.x - a.x, b.y-a.y)
        if (Math.abs(delta.x) > 1) {
            let rc = delta.y / delta.x
            let i_left = Qt.point(copysign(halfsize.x, delta.x), copysign(rc*halfsize.x, delta.y))
            if (Math.abs(i_left.y) < halfsize.y) {
                let result = Qt.point(i_left.x + a.x, i_left.y + a.y)
                return result
            }
        }
        let rc = delta.x / delta.y
        let i_top = Qt.point(copysign(rc*halfsize.y, delta.x), copysign(halfsize.y, delta.y))
        let result = Qt.point(i_top.x + a.x, i_top.y + a.y)
        return result
    }
}
 
