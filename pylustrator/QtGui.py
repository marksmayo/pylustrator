#!/usr/bin/env python
# -*- coding: utf-8 -*-
# QtGui.py

# Copyright (c) 2016-2020, Richard Gerum
#
# This file is part of Pylustrator.
#
# Pylustrator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pylustrator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pylustrator. If not, see <http://www.gnu.org/licenses/>

from qtpy import QtCore, QtWidgets, QtGui
import qtawesome as qta

import numpy as np
import matplotlib.pyplot as plt
from qtpy import API_NAME as QT_API_NAME
if QT_API_NAME.startswith("PyQt4"):
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
    from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
else:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
    from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from .matplotlibwidget import MatplotlibWidget
from matplotlib import _pylab_helpers
from matplotlib.figure import Figure
from matplotlib.artist import Artist
import matplotlib as mpl
import qtawesome as qta

from .QtShortCuts import QDragableColor

import sys


def my_excepthook(type, value, tback):
    sys.__excepthook__(type, value, tback)


sys.excepthook = my_excepthook

""" Matplotlib overload """
figures = {}
app = None


def initialize():
    """ patch figure and show to display the color chooser GUI """
    global app
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    plt.show = show
    plt.figure = figure


def show():
    """ the patched show to display the color choose gui """
    global figures
    # iterate over figures
    for figure in figures:
        # get the window
        window = figures[figure].window
        # and show it
        window.show()
    # execute the application
    app.exec_()


def figure(num=None, figsize=None, *args, **kwargs):
    """ the patched figure to initialize to color chooser GUI """
    global figures
    # if num is not defined create a new number
    if num is None:
        num = len(figures)
    # if number is not defined
    if num not in figures.keys():
        # create a new window and store it
        canvas = PlotWindow(num, *args, **kwargs).canvas
        figures[num] = canvas
    # get the canvas of the figure
    canvas = figures[num]
    # set the size if it is defined
    if figsize is not None:
        figures[num].window.setGeometry(100, 100, figsize[0] * 80, figsize[1] * 80)
    # set the figure as the active figure
    _pylab_helpers.Gcf.set_active(canvas.manager)
    # return the figure
    return canvas.figure


""" Figure list functions """


def addChildren(color_artists: list, parent: Artist):
    """ find all the children of an Artist that use a color """
    for artist in parent.get_children():
        # ignore empty texts
        if isinstance(artist, mpl.text.Text) and artist.get_text() == "":
            continue

        # omit the helper objects generated by pylustrator
        if getattr(artist, "_no_save", False):
            continue

        # add the children of the item (not for text or ticks)
        if not isinstance(artist, (mpl.text.Text, mpl.axis.XTick, mpl.axis.YTick)):
            addChildren(color_artists, artist)

        # iterate over the elements
        for color_type_name in ["edgecolor", "facecolor", "color", "markeredgecolor", "markerfacecolor"]:
            colors = getattr(artist, "get_" + color_type_name, lambda: None)()
            # ignore colors that are not set
            if colors is None or len(colors) == 0:
                continue

            # convert to array
            if (not (isinstance(colors, np.ndarray) and len(colors.shape) > 1) and not isinstance(colors, list)) or \
                    getattr(colors, "cmap", None) is not None:
                colors = [colors]

            # iterate over the colors
            for color in colors:
                # test if it is a colormap
                try:
                    cmap = color.cmap
                    value = color.value
                except AttributeError:
                    cmap = None

                try:
                    mpl.colors.to_hex(color)
                except ValueError:
                    continue

                # omit blacks and whites
                if mpl.colors.to_hex(color) == "#000000" or mpl.colors.to_hex(color) == "#ffffff":
                    continue

                # if we have a colormap
                if cmap:
                    if getattr(cmap, "get_color", None):
                        # iterate over the colors of the colormap
                        for index, color in enumerate(cmap.get_color()):
                            # convert to hex
                            color = mpl.colors.to_hex(color)
                            # check if it is already in the dictionary
                            if color not in color_artists:
                                color_artists[color] = []
                            # add the artist
                            color_artists[color].append([color_type_name, artist, value, cmap, index])
                    else:
                        # check if it is already in the dictionary
                        if cmap not in color_artists:
                            color_artists[cmap] = []
                        color_artists[cmap].append([color_type_name, artist, value, cmap, value])
                else:
                    # ignore transparent colors
                    if mpl.colors.to_rgba(color)[3] == 0:
                        continue
                    # convert to hey
                    color = mpl.colors.to_hex(color)
                    # check if it is already in the dictionary
                    if color not in color_artists:
                        color_artists[color] = []
                    # add the artist
                    color_artists[color].append([color_type_name, artist, None, None, None])


def figureListColors(figure: Figure):
    """ add all artist with colors to a list in the figure """
    figure.color_artists = {}
    addChildren(figure.color_artists, figure)


def figureSwapColor(figure: Figure, new_color: str, color_base: str):
    """ swap two colors of a figure """
    if getattr(figure, "color_artists", None) is None:
        figureListColors(figure)
    changed_cmaps = []
    maps = plt.colormaps()
    for data in figure.color_artists[color_base]:
        # get the data
        color_type_name, artist, value, cmap, index = data
        # if the color is part of a colormap, update the colormap
        if cmap:
            # update colormap
            if cmap not in changed_cmaps:
                changed_cmaps.append(cmap)
                if getattr(cmap, "set_color", None) is not None:
                    cmap.set_color(new_color, index)
            if getattr(cmap, "set_color", None) is None:
                if new_color in maps:
                    cmap = plt.get_cmap(new_color)
                else:
                    getattr(artist, "set_" + color_type_name)(new_color)
                    artist.figure.change_tracker.addChange(artist,
                                                           ".set_" + color_type_name + "(\"%s\")" % (new_color,))
                    continue
            # use the attributes setter method
            getattr(artist, "set_" + color_type_name)(cmap(value))
            artist.figure.change_tracker.addChange(artist, ".set_" + color_type_name + "(plt.get_cmap(\"%s\")(%s))" % (
            cmap.name, str(value)))
        else:
            if new_color in maps:
                cmap = plt.get_cmap(new_color)
                getattr(artist, "set_" + color_type_name)(cmap(0))
                artist.figure.change_tracker.addChange(artist,
                                                       ".set_" + color_type_name + "(plt.get_cmap(\"%s\")(%s))" % (
                                                           cmap.name, str(0)))
            else:
                # use the attributes setter method
                getattr(artist, "set_" + color_type_name)(new_color)
                artist.figure.change_tracker.addChange(artist, ".set_" + color_type_name + "(\"%s\")" % (new_color,))


""" Window """


class ColorChooserWidget(QtWidgets.QWidget):
    trigger_no_update = False

    def __init__(self, parent: QtWidgets, canvas: Canvas):
        """ A widget to display all curently used colors and let the user switch them.

        Args:
            parent: the parent widget
            canvas: the figure's canvas element
        """
        QtWidgets.QWidget.__init__(self)

        # initialize color artist dict
        self.color_artists = {}
        # tracks how many colors have changed to make sure
        # that updateColors is only called after a
        # full swap this means 2 colors change
        self.swap_counter = 0

        # add update push button
        self.button_update = QtWidgets.QPushButton(qta.icon("ei.refresh"), "update")
        self.button_update.clicked.connect(self.updateColors)

        # add color chooser layout
        self.layout_right = QtWidgets.QVBoxLayout(self)
        self.layout_right.addWidget(self.button_update)

        self.layout_colors = QtWidgets.QVBoxLayout()
        self.layout_right.addLayout(self.layout_colors)

        self.layout_colors2 = QtWidgets.QVBoxLayout()
        self.layout_right.addLayout(self.layout_colors2)

        self.layout_buttons = QtWidgets.QVBoxLayout()
        self.layout_right.addLayout(self.layout_buttons)
        self.button_save = QtWidgets.QPushButton("Save Colors")
        self.button_save.clicked.connect(self.saveColors)
        self.layout_buttons.addWidget(self.button_save)
        self.button_load = QtWidgets.QPushButton("Load Colors")
        self.button_load.clicked.connect(self.loadColors)
        self.layout_buttons.addWidget(self.button_load)

        self.canvas = canvas

        # add a text widget to allow easy copy and paste
        self.colors_text_widget = QtWidgets.QTextEdit()
        self.colors_text_widget.setAcceptRichText(False)
        self.layout_colors2.addWidget(self.colors_text_widget)
        self.colors_text_widget.textChanged.connect(self.colors_changed)

    def saveColors(self):
        """ save the colors to a .txt file """
        path = QtWidgets.QFileDialog.getSaveFileName(self, "Save Color File", getattr(self, "last_save_folder", None),
                                                     "Text File *.txt")
        if isinstance(path, tuple):
            path = str(path[0])
        else:
            path = str(path)
        if not path:
            return
        self.last_save_folder = path
        with open(path, "w") as fp:
            fp.write(self.colors_text_widget.toPlainText())

    def loadColors(self):
        """ load a list of colors from a .txt file """
        path = QtWidgets.QFileDialog.getOpenFileName(self, "Open Color File", getattr(self, "last_save_folder", None),
                                                     "Text File *.txt")
        if isinstance(path, tuple):
            path = str(path[0])
        else:
            path = str(path)
        if not path:
            return
        self.last_save_folder = path
        with open(path, "r") as fp:
            self.colors_text_widget.setText(fp.read())

    def addColorButton(self, color: str, basecolor: str = None):
        """ add a button for the given color """
        try:
            button = QDragableColor(mpl.colors.to_hex(color))
        except ValueError:
            button = QDragableColor(color)
        self.layout_colors.addWidget(button)
        button.color_changed.connect(lambda c: self.colorChanged(c, color_base=basecolor))
        button.color_changed_by_color_picker.connect(lambda e: self.resetSwapcounter(e))
        if basecolor:
            self.color_buttons[basecolor] = button
        self.color_buttons_list.append(button)

    def colorChanged(self, c, color_base):
        """ update a color when it is changed
        if colors are swapped then first change both colors  and then update the text list of colors
        """
        self.color_selected(c, color_base)

        # call updateColors after 2 colors have swapped
        self.swap_counter += 1
        if self.swap_counter == 2:
            self.swap_counter = 0
            self.updateColors()

    def resetSwapcounter(self, _):
        """ when a color changed using the color picker the swap counter is reset """
        self.swap_counter = 0
        self.updateColors()

    def updateColors(self):
        """ update the text list of colors """
        # add recursively all artists of the figure
        figureListColors(self.canvas.figure)
        self.color_artists = list(self.canvas.figure.color_artists)

        # iterate over all colors
        self.color_buttons = {}
        self.color_buttons_list = []

        while self.layout_colors.takeAt(0):
            pass

        # for color_button in self.color_buttons_list:
        #    color_button.deleteLater()
        #    color_button.set
        self.color_buttons_list = []

        for color in self.color_artists[:20]:
            self.addColorButton(color, color)

        self.trigger_no_update = True
        try:
            def colorToText(color):
                try:
                    return mpl.colors.to_hex(color)
                except ValueError:
                    return color

            self.colors_text_widget.setText("\n".join([colorToText(color) for color in self.color_artists[:10]]))
        finally:
            self.trigger_no_update = False

        # update the canvas dimensions
        self.canvas.updateGeometry()

    def colors_changed(self):
        """ when the colors changed """
        if self.trigger_no_update:
            return
        maps = plt.colormaps()
        # when the colors in the text edit changed
        for index, color in enumerate(self.colors_text_widget.toPlainText().split("\n")):
            try:
                color = mpl.colors.to_hex(color.strip())
            except ValueError:
                if color not in maps:
                    continue
            if len(self.color_buttons_list) <= index:
                self.addColorButton(color)
            self.color_buttons_list[index].setColor(color)

    def color_selected(self, new_color: str, color_base: str):
        """ switch two colors """
        if color_base is None:
            return
        figureSwapColor(self.canvas.figure, new_color, color_base)
        # redraw the plot
        self.canvas.draw()


class PlotWindow(QtWidgets.QWidget):
    def __init__(self, number, *args, **kwargs):
        """ An alternative to the pylustrator gui that only displays the color chooser. Mainly for testing purpose. """
        QtWidgets.QWidget.__init__(self)

        # widget layout and elements
        self.setWindowTitle("Figure %s" % number)
        self.setWindowIcon(qta.icon("fa5.bar-chart"))
        self.layout_main = QtWidgets.QHBoxLayout(self)

        # add plot layout
        self.layout_plot = QtWidgets.QVBoxLayout(self)
        self.layout_main.addLayout(self.layout_plot)

        # add plot canvas
        self.canvas = MatplotlibWidget(self)
        self.canvas.window = self
        self.layout_plot.addWidget(self.canvas)
        _pylab_helpers.Gcf.set_active(self.canvas.manager)

        # add toolbar
        self.navi_toolbar = NavigationToolbar(self.canvas, self)
        self.layout_plot.addWidget(self.navi_toolbar)
        self.layout_plot.addStretch()

        self.colorWidget = ColorChooserWidget(self, self.canvas)
        self.layout_main.addWidget(self.colorWidget)

    def showEvent(self, a0: QtGui.QShowEvent):
        # update the colors
        self.colorWidget.updateColors()
