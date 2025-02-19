import QtQuick 2.15
import QtQuick.Shapes 1.12

Item {
    property var a_details
    property var b_details

    property var start_point: a_details.intersect(b_details.getCenter())
    property var end_point: b_details.intersect(a_details.getCenter())

    Shape {
        ShapePath {
            strokeColor: "black"
            strokeWidth: 1
            
            //property var start_point: a_details.getCenter()
            //property var end_point: b_details.getCenter()
            
            //startX: a_details.getCenter().x
            //startY: a_details.getCenter().y
            startX: start_point.x
            startY: start_point.y
            
            PathLine {
                //x: b_details.getCenter().x
                //y: b_details.getCenter().y
                x: end_point.x
                y: end_point.y
            }
        }
    }
}
