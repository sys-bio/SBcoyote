"""The main View class and associated widgets.
"""
# pylint: disable=maybe-no-member
import wx
import wx.lib.agw.flatnotebook as fnb
import copy
from typing import Callable, List, Dict, Any, Optional, Set, Tuple
from .canvas.events import EVT_DID_DRAG_MOVE_NODES, EVT_DID_DRAG_RESIZE_NODES, \
    EVT_SELECTION_DID_UPDATE, EVT_DID_UPDATE_CANVAS
from .canvas.canvas import Canvas, InputMode
from .canvas.data import Node, Reaction
from .config import settings, theme
from .forms import NodeForm, ReactionForm
from .mvc import IController, IView
from .overlays import ButtonGroup


class EditPanel(fnb.FlatNotebook):
    """Panel that displays and allows editing of the details of a node.

    Attributes
        node_form: The actual form widget. This is at the same level as null_message. TODO
        null_message: The widget displayed in place of the form,  when nothing is selected.
    """
    node_form: wx.Panel
    reaction_form: wx.Panel
    null_message: wx.StaticText
    FNB_STYLE = fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS | fnb.FNB_NODRAG | fnb.FNB_VC8

    def __init__(self, parent, canvas: Canvas, controller: IController, **kw):
        super().__init__(parent, agwStyle=EditPanel.FNB_STYLE, **kw)

        self.canvas = canvas

        self.node_form = NodeForm(self, canvas, controller)
        self.reaction_form = ReactionForm(self, canvas, controller)

        self.null_message = wx.Panel(self)
        text = wx.StaticText(self.null_message, label="Nothing is selected.", style=wx.ALIGN_CENTER)
        null_sizer = wx.BoxSizer(wx.HORIZONTAL)
        null_sizer.Add(text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)
        self.null_message.SetSizer(null_sizer)
        self.SetCustomPage(self.null_message)

        self.node_form.Hide()
        self.reaction_form.Hide()
        # overall sizer for alternating form and "nothing selected" displays
        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        #sizer.Add(null_message, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)
        # self.SetSizer(sizer)

        canvas.Bind(EVT_DID_UPDATE_CANVAS, self.OnDidUpdateCanvas)
        canvas.Bind(EVT_SELECTION_DID_UPDATE, self.OnSelectionDidUpdate)
        canvas.Bind(EVT_DID_DRAG_MOVE_NODES, self.OnDidDragMoveNodes)
        canvas.Bind(EVT_DID_DRAG_RESIZE_NODES, self.OnDidDragResizeNodes)

    def OnDidUpdateCanvas(self, evt):
        self.node_form.UpdateNodes(evt.nodes)
        self.reaction_form.UpdateReactions(evt.reactions)

    def OnSelectionDidUpdate(self, evt):
        should_show_nodes = len(evt.node_idx) != 0
        should_show_reactions = len(evt.reaction_idx) != 0

        node_index = -1
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == self.node_form:
                node_index = i
                break

        cur_page = self.GetCurrentPage()

        if should_show_nodes:
            self.node_form.UpdateNodeSelection(evt.node_idx)
            if node_index == -1:
                self.InsertPage(0, self.node_form, 'Nodes')
                self.node_form.Show()
        elif node_index != -1:
            # find and remove existing page
            self.RemovePage(node_index)
            self.node_form.Hide()

        reaction_index = -1
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == self.reaction_form:
                reaction_index = i
                break

        if should_show_reactions:
            self.reaction_form.UpdateReactionSelection(evt.reaction_idx)
            if reaction_index == -1:
                self.AddPage(self.reaction_form, 'Reactions')
                self.reaction_form.Show()
        elif reaction_index != -1:
            self.RemovePage(reaction_index)
            self.reaction_form.Hide()

        # set the active tab to the same as before
        for i in range(self.GetPageCount()):
            if self.GetPage(i) == cur_page:
                self.SetSelection(i)
                break
        # need to reset focus to canvas, since for some reason FlatNotebook sets focus to the first
        # field in a notebook page after it is added.
        self.GetSizer().Layout()

        # need to manually show this for some reason
        if not should_show_nodes and not should_show_reactions:
            self.null_message.Show()

    def OnDidDragMoveNodes(self, evt):
        self.node_form.UpdateDidDragMoveNodes()

    def OnDidDragResizeNodes(self, evt):
        self.node_form.UpdateDidDragResizeNodes()


class Toolbar(wx.Panel):
    """ModePanel at the top of the app."""

    def __init__(self, parent, controller: IController, zoom_callback, edit_panel_callback, **kw):
        super().__init__(parent, **kw)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        zoom_in_btn = wx.Button(self, label="Zoom In")
        # TODO make this a method
        undo_button = wx.Button(self, label="Undo")
        sizer.Add(undo_button, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        undo_button.Bind(wx.EVT_BUTTON, lambda _: controller.try_undo())

        redo_button = wx.Button(self, label="Redo")
        sizer.Add(redo_button, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        redo_button.Bind(wx.EVT_BUTTON, lambda _: controller.try_redo())

        sizer.Add(zoom_in_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_in_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(True))

        zoom_out_btn = wx.Button(self, label="Zoom Out")
        sizer.Add(zoom_out_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_out_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(False))

        # Note: Right align after this
        sizer.Add((0, 0), proportion=1, flag=wx.EXPAND)

        toggle_panel_button = wx.Button(self, label="Toggle Details")
        sizer.Add(toggle_panel_button, wx.SizerFlags().Align(
            wx.ALIGN_CENTER_VERTICAL).Border(wx.RIGHT, 10))
        toggle_panel_button.Bind(wx.EVT_BUTTON, edit_panel_callback)

        self.SetSizer(sizer)


class ModePanel(wx.Panel):
    """ModePanel at the left of the app."""

    def __init__(self, *args, toggle_callback, canvas: Canvas, **kw):
        super().__init__(*args, **kw)

        self.btn_group = ButtonGroup(toggle_callback)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.AppendModeButton('Select', InputMode.SELECT, sizer)
        self.AppendModeButton('Add', InputMode.ADD, sizer)
        self.AppendModeButton('Zoom', InputMode.ZOOM, sizer)

        self.AppendSeparator(sizer)
        self.AppendNormalButton('Reactants', canvas.MarkSelectedAsReactants,
                                sizer, tooltip='Mark selected nodes as reactants')
        self.AppendNormalButton('Products', canvas.MarkSelectedAsProducts,
                                sizer, tooltip='Mark selected nodes as products')
        self.AppendNormalButton('Create Rxn', canvas.CreateReactionFromMarked,
                                sizer, tooltip='Create reaction from marked reactants and products')

        self.SetSizer(sizer)

    def AppendModeButton(self, label: str, mode: InputMode, sizer: wx.Sizer):
        btn = wx.ToggleButton(self, label=label)
        sizer.Add(btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        self.btn_group.AddButton(btn, mode)

    def AppendNormalButton(self, label: str, callback, sizer: wx.Sizer, tooltip: str = None):
        btn = wx.Button(self, label=label)
        if tooltip is not None:
            btn.SetToolTip(tooltip)
        btn.Bind(wx.EVT_BUTTON, lambda _: callback())
        sizer.Add(btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))

    def AppendSeparator(self, sizer: wx.Sizer):
        line = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        sizer.Add(line, wx.SizerFlags().Expand().Border(wx.TOP, 10))


class MainPanel(wx.Panel):
    """The main panel, which is the only chlid of the root Frame."""
    controller: IController
    theme: Dict[str, Any]
    canvas: Canvas
    mode_panel: ModePanel
    toolbar: Toolbar
    edit_panel: EditPanel

    def __init__(self, parent, controller: IController):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(theme['overall_bg'])
        self.controller = controller

        self.canvas = Canvas(self.controller, self,
                             size=(theme['canvas_width'], theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'], 4 * theme['canvas_height']),
                             )
        self.canvas.SetScrollRate(10, 10)

        # The bg of the available canvas will be drawn by canvas in OnPaint()
        self.canvas.SetBackgroundColour(theme['canvas_outside_bg'])

        def set_input_mode(ident):
            self.canvas.input_mode = ident

        # create a panel in the frame
        self.mode_panel = ModePanel(self,
                                    size=(theme['mode_panel_width'],
                                          theme['canvas_height']),
                                    toggle_callback=set_input_mode,
                                    canvas=self.canvas,
                                    )
        self.mode_panel.SetBackgroundColour(theme['toolbar_bg'])

        toolbar_width = theme['canvas_width'] + theme['edit_panel_width'] + theme['vgap']
        self.toolbar = Toolbar(self, controller,
                               size=(toolbar_width, theme['toolbar_height']),
                               zoom_callback=self.canvas.ZoomCenter,
                               edit_panel_callback=self.ToggleEditPanel)
        self.toolbar.SetBackgroundColour(theme['toolbar_bg'])

        self.edit_panel = EditPanel(self, self.canvas, self.controller,
                                    size=(theme['edit_panel_width'],
                                          theme['canvas_height']))
        self.edit_panel.SetBackgroundColour(theme['toolbar_bg'])

        # and create a sizer to manage the layout of child widgets
        sizer = wx.GridBagSizer(vgap=theme['vgap'], hgap=theme['hgap'])

        sizer.Add(self.toolbar, wx.GBPosition(0, 1), wx.GBSpan(1, 2), flag=wx.EXPAND)
        sizer.Add(self.mode_panel, wx.GBPosition(1, 0), flag=wx.EXPAND)
        sizer.Add(self.canvas, wx.GBPosition(1, 1),  flag=wx.EXPAND)
        sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)

        # allow the canvas to grow
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # Set the sizer and *prevent the user from resizing it to a smaller size
        self.SetSizerAndFit(sizer)

    def OnNodeDrop(self, obj: wx.Window, pos: wx.Point):
        if obj == self.canvas:
            self.canvas.OnNodeDrop(pos)

    def ToggleEditPanel(self, evt):
        sizer = self.GetSizer()
        if self.edit_panel.IsShown():
            sizer.Detach(self.edit_panel)
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 2))
            self.edit_panel.Hide()
        else:
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 1))
            sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)
            self.edit_panel.Show()

        self.Layout()


class MyFrame(wx.Frame):
    """The main frame."""

    def __init__(self, controller: IController, **kw):
        super().__init__(None, style=wx.DEFAULT_FRAME_STYLE | wx.WS_EX_PROCESS_UI_UPDATES, **kw)

        status_fields = settings['status_fields']
        assert status_fields is not None
        self.CreateStatusBar(len(settings['status_fields']))
        self.SetStatusWidths([width for _, width in status_fields])
        self.main_panel = MainPanel(self, controller)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)

        canvas = self.main_panel.canvas

        entries = list()
        menu_bar = wx.MenuBar()

        self.menu_events = list()
        file_menu = wx.Menu()
        self.AddMenuItem(file_menu, 'E&xit', 'Exit application', lambda _: self.Close(), entries,
                         id_=wx.ID_EXIT)

        edit_menu = wx.Menu()
        self.AddMenuItem(edit_menu, '&Undo', 'Undo action', lambda _: controller.try_undo(),
                         entries, key=(wx.ACCEL_CTRL, ord('Z')))
        self.AddMenuItem(edit_menu, '&Redo', 'Redo action', lambda _: controller.try_redo(),
                         entries, key=(wx.ACCEL_CTRL, ord('Y')))
        edit_menu.AppendSeparator()
        self.AddMenuItem(edit_menu, '&Copy', 'Copy selected nodes', lambda _: canvas.CopySelected(),
                         entries, key=(wx.ACCEL_CTRL, ord('C')))
        self.AddMenuItem(edit_menu, '&Paste', 'Paste selected nodes',
                         lambda _: canvas.Paste(), entries, key=(wx.ACCEL_CTRL, ord('V')))
        self.AddMenuItem(edit_menu, '&Cut', 'Cut selected nodes',
                         lambda _: canvas.CutSelected(), entries, key=(wx.ACCEL_CTRL, ord('X')))
        edit_menu.AppendSeparator()
        self.AddMenuItem(edit_menu, '&Delete selected', 'Deleted selected',
                         lambda _: canvas.DeleteSelectedNodes(), entries,
                         key=(wx.ACCEL_NORMAL, wx.WXK_DELETE))

        select_menu = wx.Menu()
        self.AddMenuItem(select_menu, 'Select &All', 'Select all',
                         lambda _: canvas.SelectAll(), entries, key=(wx.ACCEL_CTRL, ord('A')))
        self.AddMenuItem(select_menu, 'Clear Selections', 'Clear selections',
                         lambda _: canvas.ClearSelection(), entries,
                         key=(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('A')))

        view_menu = wx.Menu()
        self.AddMenuItem(view_menu, 'Zoom &In', 'Zoom in canvas', lambda _: canvas.ZoomCenter(True),
                         entries, key=(wx.ACCEL_CTRL, ord('+')))
        self.AddMenuItem(view_menu, 'Zoom &Out', 'Zoom out canvas',
                         lambda _: canvas.ZoomCenter(False), entries, key=(wx.ACCEL_CTRL, ord('-')))
        self.AddMenuItem(view_menu, '&Reset Zoom', 'Reset canva zoom',
                         lambda _: canvas.ResetZoom(), entries, key=(wx.ACCEL_CTRL, ord(' ')))

        reaction_menu = wx.Menu()
        self.AddMenuItem(reaction_menu, 'Mark Selected as &Reactants',
                         'Mark selected nodes as reactants',
                         lambda _: canvas.MarkSelectedAsReactants(), entries,
                         key=(wx.ACCEL_NORMAL, ord('S')))
        self.AddMenuItem(reaction_menu, 'Mark Selected as &Products',
                         'Mark selected nodes as products',
                         lambda _: canvas.MarkSelectedAsProducts(), entries,
                         key=(wx.ACCEL_NORMAL, ord('F')))
        self.AddMenuItem(reaction_menu, '&Create Reaction From Selected',
                         'Create reaction from selected sources and targets',
                         lambda _: canvas.CreateReactionFromMarked(), entries,
                         key=(wx.ACCEL_CTRL, ord('R')))

        menu_bar.Append(file_menu, '&File')
        menu_bar.Append(edit_menu, '&Edit')
        menu_bar.Append(select_menu, '&Select')
        menu_bar.Append(view_menu, '&View')
        menu_bar.Append(reaction_menu, '&Reaction')

        atable = wx.AcceleratorTable(entries)

        self.SetMenuBar(menu_bar)
        self.atable = atable
        canvas.SetAcceleratorTable(atable)

        self.OverrideAccelTable(self)

        # set sizer at the end, after adding the menus.
        self.SetSizerAndFit(sizer)
        self.Center()

    def AddMenuItem(self, menu: wx.Menu, text: str, help_text: str, callback: Callable,
                    entries: List, key: Tuple[Any, wx.KeyCode] = None, id_: str = None):
        if id_ is None:
            id_ = wx.NewId()

        shortcut = ''
        if key is not None:
            entry = wx.AcceleratorEntry(key[0], key[1], id_)
            entries.append(entry)
            shortcut = entry.ToString()

        item = menu.Append(id_, '{}\t{}'.format(text, shortcut), help_text)
        self.Bind(wx.EVT_MENU, callback, item)
        self.menu_events.append((callback, item))

    def OverrideAccelTable(self, widget):
        # TODO document
        if isinstance(widget, wx.TextCtrl):
            def OnFocus(evt):
                for cb, item in self.menu_events:
                    self.Unbind(wx.EVT_MENU, handler=cb, source=item)
                # For some reason, we need to do this for both self and menubar to disable the
                # AcceleratorTable. Don't ever lose this sacred knowledge, for it came at the cost
                # of 50 minutes.
                self.SetAcceleratorTable(wx.NullAcceleratorTable)
                self.GetMenuBar().SetAcceleratorTable(wx.NullAcceleratorTable)
                evt.Skip()

            def OnUnfocus(evt):
                for cb, item in self.menu_events:
                    self.Bind(wx.EVT_MENU, handler=cb, source=item)
                self.SetAcceleratorTable(self.atable)
                evt.Skip()

            widget.Bind(wx.EVT_SET_FOCUS, OnFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, OnUnfocus)

        for child in widget.GetChildren():
            self.OverrideAccelTable(child)


class View(IView):
    """Implementation of the view class."""

    def __init__(self):
        self.controller = None

    def bind_controller(self, controller: IController):
        self.controller = controller

    def main_loop(self):
        assert self.controller is not None
        app = wx.App()
        frm = MyFrame(self.controller, title='RK Network Viewer')
        self.canvas_panel = frm.main_panel.canvas
        self.canvas_panel.RegisterAllChildren(frm)
        frm.Show()
        app.MainLoop()

    def update_all(self, nodes: List[Node], reactions: List[Reaction]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.Reset(nodes, reactions)
        self.canvas_panel.Refresh()
