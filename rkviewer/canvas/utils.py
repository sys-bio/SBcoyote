# pylint: disable=maybe-no-member
import wx
from typing import Optional, List
from ..utils import Vec2, Rect, Node


def within_rect(pos: Vec2, rect: Rect) -> bool:
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y


def draw_rect(gc: wx.GraphicsContext, rect: Rect, *, fill: Optional[wx.Colour] = None,
             border: Optional[wx.Colour] = None, border_width: float = 1):
    """Draw a rectangle on the given graphics context."""
    if fill is None and border is None:
        raise ValueError("Both 'fill' and 'border' are None, but at least one of them should be "
                         "provided")

    if border is not None and border_width == 0:
        raise ValueError("'border_width' cannot be 0 when 'border' is specified")

    x, y = rect.position
    width, height = rect.size

    # set up brush and pen if applicable
    if fill is not None:
        brush = wx.Brush(fill, wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
    if border is not None:
        pen = gc.CreatePen(wx.GraphicsPenInfo(border).Width(border_width))
        gc.SetPen(pen)

    # draw rect
    path = gc.CreatePath()
    path.AddRectangle(x, y, width, height)

    # finish drawing if applicable
    if fill is not None:
        gc.FillPath(path)
    if border is not None:
        gc.StrokePath(path)


def get_bounding_rect(nodes: List[Node], padding: float = 0) -> Rect:
    min_x = min(n.s_position.x for n in nodes)
    min_y = min(n.s_position.y for n in nodes)
    max_x = max(n.s_position.x + n.s_size.x for n in nodes)
    max_y = max(n.s_position.y + n.s_size.y for n in nodes)
    size_x = max_x - min_x + padding * 2
    size_y = max_y - min_y + padding * 2
    return Rect(Vec2(min_x - padding, min_y - padding), Vec2(size_x, size_y))


def clamp_rect_pos(rect: Rect, bounds: Rect, padding = 0) -> Vec2:
    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.size - rect.size - Vec2.repeat(padding)
    ret = rect.position
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def clamp_point(pos: Vec2, bounds: Rect, padding = 0) -> Vec2:
    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.size - Vec2.repeat(padding)
    ret = pos
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def rects_intersect(r1: Rect, r2: Rect) -> bool:
    botright1 = r1.position + r1.size
    botright2 = r2.position + r2.size

    for axis in [0, 1]:
        if botright1[axis] <= r2.position[axis] or botright2[axis] <= r1.position[axis]:
            return False

    return True
