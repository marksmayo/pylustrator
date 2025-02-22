#!/usr/bin/env python
# -*- coding: utf-8 -*-
# QtShortCuts.py

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

import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib.backends.qt_compat import QtCore, QtGui, QtWidgets

""" Color Chooser. """


class QDragableColor(QtWidgets.QLabel):
    """ A color widget that can be dragged onto another QDragableColor widget to exchange the two colors.
    Alternatively it can be right-clicked to select either a color or a colormap through their respective menus.
    The button can represent either a single color or a colormap.
    """

    color_changed = QtCore.Signal(str)
    color_changed_by_color_picker = QtCore.Signal(bool)

    def __init__(self, value: str):
        """ Initialize with a color. """
        super().__init__(value)
        import matplotlib.pyplot as plt
        self.maps = plt.colormaps()
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignHCenter)
        self.setColor(value, True)

    def getBackground(self) -> str:
        """ Get the background of the color button. """
        try:
            cmap = plt.get_cmap(self.color)
        except Exception:
            return ""
        text = "background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, "
        N = 10
        for i in range(N):
            i = i / (N - 1)
            text += f"stop: {i:.2f} {mpl.colors.to_hex(cmap(i))}, "
        text = text[:-2] + ");"
        return text

    def setColor(self, value: str, no_signal=False):
        """ Set the current color. """
        # display and save the new color
        self.color = value
        self.setText(value)
        self.color_changed.emit(value)
        if value in self.maps:
            self.setStyleSheet("text-align: center; border: 2px solid black; padding: 0.1em; " + self.getBackground())
        else:
            self.setStyleSheet(f"text-align: center; background-color: {value}; border: 2px solid black; padding: 0.1em; ")

    def getColor(self) -> str:
        """ Get the current color. """
        # return the color
        return self.color

    def mousePressEvent(self, event):
        """ When a mouse button is pressed. """
        # a left mouse button lets the user drag the color
        if event.button() == QtCore.Qt.LeftButton:
            drag = QtGui.QDrag(self)
            drag.setPixmap(self.grab())
            mime = QtCore.QMimeData()
            mime.setText(self.color)
            drag.setMimeData(mime)
            self.setStyleSheet("background-color: lightgray; border: 2px solid gray; padding: 0.1em; ")
            self.setDisabled(True)
            self.setText("")
            drag.exec()
            self.setText(self.color)
            self.setDisabled(False)
            if self.color in self.maps:
                self.setStyleSheet("text-align: center; border: 2px solid black; padding: 0.1em; " + self.getBackground())
            else:
                self.setStyleSheet(f"text-align: center; background-color: {self.color}; border: 2px solid black; padding: 0.1em; ")
        # a right mouse button opens a color choose menu
        elif event.button() == QtCore.Qt.RightButton:
            self.openDialog()

    def dragEnterEvent(self, event):
        """ When a color widget is dragged over the current widget. """
        if event.mimeData().hasFormat("text/plain") and event.source() != self:
            event.acceptProposedAction()
            if self.color in self.maps:
                self.setStyleSheet("border: 2px solid red; padding: 0.1em; " + self.getBackground())
            else:
                self.setStyleSheet(f"background-color: {self.color}; border: 2px solid red; padding: 0.1em; ")

    def dragLeaveEvent(self, event):
        """ When the color widget which is dragged leaves the area of this widget. """
        if self.color in self.maps:
            self.setStyleSheet("border: 2px solid black; padding: 0.1em; " + self.getBackground())
        else:
            self.setStyleSheet(f"background-color: {self.color}; border: 2px solid black; padding: 0.1em; ")

    def dropEvent(self, event):
        """ When a color widget is dropped here, exchange the two colors. """
        color = event.source().getColor()
        event.source().setColor(self.getColor())
        self.setColor(color)

    def openDialog(self):
        """ Open a color choosed dialog. """
        if self.color in self.maps:
            dialog = ColorMapChoose(self.parent(), self.color)
            colormap, selected = dialog.exec()
            if selected is False:
                return
            self.setColor(colormap)
        else:
            # get new color from color picker
            qcolor = QtGui.QColor(*tuple(int(x * 255) for x in mpl.colors.to_rgb(self.getColor())))
            color = QtWidgets.QColorDialog.getColor(qcolor, self.parent())
            # if a color is set, apply it
            if color.isValid():
                color = "#%02x%02x%02x" % color.getRgb()[:3]
                self.setColor(color)
                self.color_changed_by_color_picker.emit(True)


class ColorMapChoose(QtWidgets.QDialog):
    """ A dialog to select a colormap. """

    result = ""

    def __init__(self, parent: QtWidgets.QWidget, map):
        """ Initialize the dialog with all the colormap of matplotlib. """
        QtWidgets.QDialog.__init__(self, parent)
        main_layout = QtWidgets.QVBoxLayout(self)
        self.layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(self.layout)
        button_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(button_layout)
        self.button_cancel = QtWidgets.QPushButton("Cancel")
        self.button_cancel.clicked.connect(lambda _: self.done(0))
        button_layout.addStretch()
        button_layout.addWidget(self.button_cancel)

        self.maps = plt.colormaps()
        self.buttons = []
        self.setWindowTitle("Select colormap")

        # Have colormaps separated into categories:
        # http://matplotlib.org/examples/color/colormaps_reference.html
        cmaps = [('Perceptually Uniform Sequential', [
            'viridis', 'plasma', 'inferno', 'magma']),
            ('Sequential', [
             'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
             'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
             'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']),
            ('Sequential (2)', [
             'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
             'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
             'hot', 'afmhot', 'gist_heat', 'copper']),
            ('Diverging', [
             'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
             'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
            ('Qualitative', [
             'Pastel1', 'Pastel2', 'Paired', 'Accent',
             'Dark2', 'Set1', 'Set2', 'Set3',
             'tab10', 'tab20', 'tab20b', 'tab20c']),
            ('Miscellaneous', [
             'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
             'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg', 'hsv',
             'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'])]

        for cmap_category, cmap_list in cmaps:
            layout = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(cmap_category)
            layout.addWidget(label)
            label.setFixedWidth(150)
            for cmap in cmap_list:
                button = QtWidgets.QPushButton(cmap)
                button.setStyleSheet("text-align: center; border: 2px solid black; " + self.getBackground(cmap))
                button.clicked.connect(lambda _, cmap=cmap: self.buttonClicked(cmap))
                self.buttons.append(button)
                layout.addWidget(button)
            layout.addStretch()
            self.layout.addLayout(layout)

    def buttonClicked(self, text: str):
        """ The used as selected a colormap, we are done. """
        self.result = text
        self.done(1)

    def exec(self):
        """ Execute the dialog and return the result. """
        result = QtWidgets.QDialog.exec(self)
        return self.result, result == 1

    def getBackground(self, color: str) -> str:
        """ Convert a colormap to a gradient background. """
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        try:
            cmap = plt.get_cmap(color)
        except Exception:
            return ""
        text = "background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, "
        N = 10
        for i in range(N):
            i = i / (N - 1)
            text += f"stop: {i:.2f} {mpl.colors.to_hex(cmap(i))}, "
        text = text[:-2] + ");"
        return text
