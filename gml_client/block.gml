

enum CornerPositions{
    TL, BL, TR, BR
}


enum ShapeDescriptor {
    StyledPath(fn(float, float, float, float, Style) -> int),
    Rect,
    Circle
}


struct BlockShapeModel {
    property style: Style,
    property shape: ShapeDescriptor
}

widget block_shape {
    property x: float,
    property y: float,
    property width: float,
    property height: float,
    property model: BlockShapeModel,
    
    item main_rect: match model.shape {
        ShapeDescriptor.Rect => rect(x, y, x+width, y+height),
        ShapeDescriptor.StyledPath(func) => shape(d: func(x, y, width, height, model.style))
    },
    
    fsm fsm1 {
        state decorated {
            item CornerPositions.foreach(|p| {
                match p {
                CornerPositions.TL => circle(x:x, y:y, r:5,
                    onDragStart: |pos|start_size=Pos{x:width, y:height},
                    onDrag: |pos, delta|{x=pos.x; y=pos.y; width=start_size.x-delta.x; height=start_size.y-delta.y;}),
                CornerPositions.TR => circle{x:x+width, y:y, r:5,
                    onDragStart: |pos|start_size=Pos{width, height},
                    onDrag: |pos, delta|{y=pos.y; width=start_size.x+delta.x; height=start_size.y-delta.y;}},
                CornerPositions.BR => circle{x:x+width, y:y+height, r:5,
                    onDragStart: |pos|start_size=Pos{width, height},
                    onDrag: |pos, delta|{width=start_size.x+delta.x; height=start_size.y+delta.y;}},
                CornerPositions.BL => circle{x:x, y:y+height, r:5,
                    onDragStart: |pos|start_size=Pos{width, height},
                    onDrag: |pos, delta|{x=pos.x; width=start_size.x-delta.x; height=start_size.y+delta.y;}},
                }
            })
        },
        state default {},
        transit from default to decorated when main_rect.clicked
    }
}



struct BlockModel {
    property shape_model: BlockShapeModel
    property text: str
}


widget block {
    property x: float,
    property y: float,
    property width: float,
    property height: float,
    property model: BlockModel,

    block_shape{x:x, y:y, width:width, height:height, model:model.shape_model}
}
