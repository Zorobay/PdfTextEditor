import enum


class RectEdge(enum.StrEnum):
    LEFT = 'Left'
    RIGHT = 'Right'
    TOP = 'Top'
    BOTTOM = 'Bottom'
    
    def is_horizontal(self) -> bool:
        return self in self.horizontal_edges()
    
    def is_vertical(self) -> bool:
        return self in self.vertical_edges()
    
    def horizontal_edges(self) -> list['RectEdge']:
        return [self.LEFT, self.RIGHT]
    
    def vertical_edges(self) -> list['RectEdge']:
        return [self.TOP, self.BOTTOM]