import QtQuick 2.15
import QtQuick.Shapes 1.12

Item {
    property var a_details
    property var b_details

    property var start_point: a_details.intersect(b_details.getCenter())
    property var end_point: b_details.intersect(a_details.getCenter())
    
    signal clicked(index: int)

    Shape {
        ShapePath {
            strokeColor: "black"
            strokeWidth: 1
            
            startX: start_point.x
            startY: start_point.y
            
            PathLine {
                x: end_point.x
                y: end_point.y
            }
        }
        Item {
            id: item
            x: Math.min(start_point.x, end_point.x) - 5
            y: Math.min(start_point.y, end_point.y) - 5
            width: Math.abs(end_point.x - start_point.x) + 10
            height: Math.abs(end_point.y - start_point.y) + 10
            
            MouseArea {
                anchors.fill: parent
                onClicked: (mouse) => {
                    let mouse_pos = Qt.point(mouse.x+item.x-start_point.x, mouse.y+item.y-start_point.y)
                    let distance = Math.abs(distanceToLine(start_point, end_point, mouse_pos))
                    if (distance < 5) {
                        console.log("line click")
                    } else {
                        console.log("Missed the line: "+distance)
                    }
                }
            }
        }
    }
    
    function pdot(p1, p2) {
        return p1.x * p2.x + p1.y * p2.y
    }
    function pdiff(p1, p2) {
        return Qt.point(p1.x-p2.x, p1.y-p2.y)
    }
    function padd(p1, p2) {
        return Qt.point(p1.x+p2.x, p1.y+p2.y)
    }
    function pscale(p, f) {
        return Qt.point(p.x*f, p.y*f)
    }
    
    
    function distanceToLine(p1, p2, dm) {
        let delta = pdiff(p2, p1);
        let length = Math.sqrt(pdot(delta, delta));

        if (length === 0) {
            return Math.sqrt(pdot(dm, dm));
        }

        let dm_proj = pscale(delta, pdot(dm, delta)/pdot(delta, delta))
        let m_dm_proj = pdiff(dm, dm_proj)
        return Math.sqrt(pdot(m_dm_proj, m_dm_proj));
    }
}
