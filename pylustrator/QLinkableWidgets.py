#!/usr/bin/env python
# -*- coding: utf-8 -*-
# QLinkableWidgets.py

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

from typing import Optional, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import transforms
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backends.qt_compat import QtCore, QtGui, QtWidgets
from matplotlib.figure import Figure
from matplotlib.text import Text

from .helper_functions import main_figure


class Linkable:
    """A class that automatically links a widget with the property of a matplotlib artist."""

    def link(self, property_name: str, signal: QtCore.Signal = None, condition: callable = None, direct: bool = False):
        self.element = None
        self.direct = direct
        self.property_name = property_name
        if direct:
            parts = property_name.split(".")
            s = self

            def get():
                target = s.element
                for part in parts:
                    target = getattr(target, part)
                return target

            def set(v):
                get()
                target = s.element
                for part in parts[:-1]:
                    target = getattr(target, part)
                setattr(target, parts[-1], v)
                return [s.element]

            self.setLinkedProperty = set
            self.getLinkedProperty = get
            self.serializeLinkedProperty = lambda x: "." + property_name + f" = {x}"
        else:
            def set(v, v_list=None):
                if v_list is None:
                    v = [v] + [v] * len(main_figure(self.element).selection.targets)
                else:
                    v = v_list

                # special treatment for the xylabels, as they are not directly the target objects
                label_object = None
                if isinstance(self.element, Text) and len(main_figure(self.element).selection.targets) and isinstance(main_figure(self.element).selection.targets[0].target, Axes):
                    for elm in main_figure(self.element).selection.targets:
                        elm = elm.target
                        if self.element == getattr(getattr(elm, "get_xaxis")(), "get_label")():
                            label_object = "x"
                            break
                        if self.element == getattr(getattr(elm, "get_yaxis")(), "get_label")():
                            label_object = "y"
                            break

                elements = []
                getattr(self.element, "set_" + property_name)(v[0])
                elements.append(self.element)
                index = 0
                for elm in main_figure(self.element).selection.targets:
                    elm = elm.target
                    # special treatment for the xylabels, as they are not directly the target objects
                    if label_object is not None:
                        elm = getattr(getattr(elm, f"get_{label_object}axis")(), "get_label")()
                    if elm != self.element:
                        try:
                            index += 1
                            getattr(elm, "set_" + property_name, None)(v[index])
                        except TypeError as err:
                            pass
                        else:
                            elements.append(elm)
                return elements

            def getAll():
                label_object = None
                if isinstance(self.element, Text) and len(main_figure(self.element).selection.targets) and isinstance(main_figure(self.element).selection.targets[0].target, Axes):
                    for elm in main_figure(self.element).selection.targets:
                        elm = elm.target
                        if self.element == getattr(getattr(elm, "get_xaxis")(), "get_label")():
                            label_object = "x"
                            break
                        if self.element == getattr(getattr(elm, "get_yaxis")(), "get_label")():
                            label_object = "y"
                            break

                values = [(self.element, property_name, getattr(self.element, "get_" + property_name)())]
                for index, elm in enumerate(main_figure(self.element).selection.targets):
                    elm = elm.target
                    # special treatment for the xylabels, as they are not directly the target objects
                    if label_object is not None:
                        elm = getattr(getattr(elm, f"get_{label_object}axis")(), "get_label")()
                    if elm != self.element:
                        try:
                            values.append([elm, property_name, getattr(elm, "get_" + property_name, None)()])
                        except TypeError as err:
                            pass
                return values

            self.setLinkedProperty = set  # lambda text: getattr(self.element, "set_"+property_name)(text)
            self.getLinkedProperty = lambda: getattr(self.element, "get_" + property_name)()
            self.getLinkedPropertyAll = getAll
            self.serializeLinkedProperty = lambda x: ".set_" + property_name + f"({x})"

        if condition is None:
            self.condition = lambda x: True
        else:
            self.condition = condition

        self.editingFinished.connect(self.updateLink)
        signal.connect(self.setTarget)

    def setTarget(self, element: Artist):
        """Set the target for the widget."""
        self.element = element
        try:
            self.set(self.getLinkedProperty())
            self.setEnabled(self.condition(element))
        except AttributeError:
            self.hide()
        else:
            self.show()

    def updateLink(self):
        """Update the linked property."""
        old_value = self.getLinkedPropertyAll()

        try:
            elements = self.setLinkedProperty(self.get())
        except AttributeError:
            return

        new_value = self.getLinkedPropertyAll()

        def save_change(element):
            if isinstance(element, mpl.figure.Figure):
                fig = element
            else:
                fig = main_figure(element)

            if isinstance(element, Text):
                fig.change_tracker.addNewTextChange(element)
            else:
                fig.change_tracker.addChange(element, self.serializeLinkedProperty(self.getSerialized()))

        def undo():
            for elem, property_name, value in old_value:
                getattr(elem, "set_" + property_name, None)(value)
                save_change(elem)

        def redo():
            for elem, property_name, value in new_value:
                getattr(elem, "set_" + property_name, None)(value)
                save_change(elem)

        element = elements[0]
        if isinstance(element, mpl.figure.Figure):
            fig = element
        else:
            fig = main_figure(element)

        fig.change_tracker.addEdit([undo, redo, "Change property"])
        fig.canvas.draw()
        main_figure(self.element).signals.figure_selection_property_changed.emit()

    def set(self, value):
        """Set the value (to be overloaded)."""
        pass

    def get(self):
        """Get the value."""
        return

    def getSerialized(self):
        """Serialize the value for saving as a command."""
        return ""


class FreeNumberInput(QtWidgets.QLineEdit):
    send_signal = True
    valueChanged = QtCore.Signal(float)

    def __init__(self):
        """ Like a QSpinBox for number import, but without min or max range or a fixed resolution.
        Especially important for the limits of logarithmic plots.

        Attributes:
            send_signal : Whether to currently emit the valueChanged signal or not (to prevent the signal from being
                emitted when the value is set by script.
            valueChanged : a signal that is emitted when the value is changed by the user
        """
        QtWidgets.QLineEdit.__init__(self)
        # self.setMaximumWidth(50)
        self.textChanged.connect(self.emitValueChanged)

    def emitValueChanged(self):
        """Connected to the textChanged signal."""
        if self.send_signal:
            try:
                value = self.value()
                self.valueChanged.emit(value)
                self.setStyleSheet("")
            except TypeError:
                self.setStyleSheet("background: #d56060; border: red")
                pass

    def value(self) -> Optional[float]:
        """Return the value of the input field."""
        try:
            return float(self.text())
        except ValueError:
            try:
                return float(self.text().replace(",", "."))
            except ValueError:
                return None

    def setValue(self, value: float):
        """Set the value of the input field."""
        self.send_signal = False
        try:
            self.setText(str(value))
            self.setCursorPosition(0)
        finally:
            self.send_signal = True


class DimensionsWidget(QtWidgets.QWidget, Linkable):
    valueChanged = QtCore.Signal(tuple)
    valueChangedX = QtCore.Signal(float)
    valueChangedY = QtCore.Signal(float)
    transform = None
    noSignal = False

    def __init__(self, layout: QtWidgets.QLayout, text: str, join: str, unit: str, free: bool = False):
        """A widget that lets the user input a pair of dimensions (e.g. widh and height).

        Args:
            layout: the layout to which to add the widget
            text: the label of the widget
            join: a text between the two parts
            unit: a unit for the values
            free: whether to use free number input widgets instead of QSpinBox
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.text = QtWidgets.QLabel(text)
        self.layout.addWidget(self.text)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if free:
            self.input1 = FreeNumberInput()
        else:
            self.input1 = QtWidgets.QDoubleSpinBox()
            self.input1.setSuffix(" " + unit)
            self.input1.setSingleStep(0.1)
            self.input1.setMaximum(99999)
            self.input1.setMinimum(-99999)
            self.input1.setMaximumWidth(100)
        self.input1.valueChanged.connect(self.onValueChangedX)
        self.layout.addWidget(self.input1)

        self.text2 = QtWidgets.QLabel(join)
        self.text2.setMaximumWidth(self.text2.fontMetrics().width(join))
        self.layout.addWidget(self.text2)

        if free:
            self.input2 = FreeNumberInput()
        else:
            self.input2 = QtWidgets.QDoubleSpinBox()
            self.input2.setSuffix(" " + unit)
            self.input2.setSingleStep(0.1)
            self.input2.setMaximum(99999)
            self.input2.setMinimum(-99999)
            self.input2.setMaximumWidth(100)
        self.input2.valueChanged.connect(self.onValueChangedY)
        self.layout.addWidget(self.input2)

        self.editingFinished = self.valueChanged

    def setLabel(self, text: str):
        """ Set the text of the label. """
        self.text.setText(text)

    def setUnit(self, unit: str):
        """ Sets the text for the unit for the values. """
        self.input1.setSuffix(" " + unit)
        self.input2.setSuffix(" " + unit)

    def setTransform(self, transform: mpl.transforms.Transform):
        """ Set the transform for the units. """
        self.transform = transform

    def onValueChangedX(self):
        """ Called when the value was changed -> emit the value changed signal. """
        if not self.noSignal:
            self.valueChangedX.emit(self.value()[0])
            self.valueChanged.emit(tuple(self.value()))

    def onValueChangedY(self):
        """ Called when the value was changed -> emit the value changed signal. """
        if not self.noSignal:
            self.valueChangedY.emit(self.value()[1])
            self.valueChanged.emit(tuple(self.value()))

    def onValueChanged(self):
        """ Called when the value was changed -> emit the value changed signal. """
        if not self.noSignal:
            self.valueChanged.emit(tuple(self.value()))

    def setValue(self, values: tuple, signal=False):
        """ Set the two values. """
        self.noSignal = True
        if self.transform:
            values = self.transform.transform(values)
        self.input1.setValue(values[0])
        self.input2.setValue(values[1])
        self.noSignal = False
        if signal is True:
            self.onValueChanged()

    def value(self):
        """ Get the value. """
        tuple = (self.input1.value(), self.input2.value())
        if self.transform:
            tuple = self.transform.inverted().transform(tuple)
        return tuple

    def get(self) -> tuple:
        """ Get the value (used for the Linkable parent class). """
        return self.value()

    def set(self, value: tuple):
        """ Set both values (used for the Linkable parent class). """
        self.setValue(value)

    def getSerialized(self) -> str:
        """ Serialize the values. """
        return ", ".join([str(i) for i in self.get()])


class TextWidget(QtWidgets.QWidget, Linkable):
    editingFinished = QtCore.Signal()
    noSignal = False
    last_text = None

    def __init__(self, layout: QtWidgets.QLayout, text: str, multiline: bool = False, horizontal: bool = True, allow_literal_decoding=False):
        """ A text input widget with a label.

        Args:
            layout: the layout to which to add the widget
            text: the label text
            multiline: whether the text input should be a single line or not
            horizontal:  whether the layout should be left or above the input
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.allow_literal_decoding = allow_literal_decoding
        if horizontal:
            self.layout = QtWidgets.QHBoxLayout(self)
        else:
            self.layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(text)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.multiline = multiline
        if multiline:
            self.input1 = QtWidgets.QTextEdit()
            self.input1.textChanged.connect(self.valueChangeEvent)
            self.input1.text = self.input1.toPlainText
        else:
            self.input1 = QtWidgets.QLineEdit()
            self.input1.editingFinished.connect(self.valueChangeEvent)
        self.layout.addWidget(self.input1)

    def valueChangeEvent(self):
        """ An event that is triggered when the text in the input field is changed. """
        if not self.noSignal and self.input1.text() != self.last_text:
            self.editingFinished.emit()

    def setLabel(self, text: str):
        """ Set the text of the label. """
        self.label.setLabel(text)

    def setText(self, text: str, signal=False):
        """ Set contents of the text input widget. """
        self.noSignal = True
        text = text.replace("\n", "\\n")
        self.last_text = text
        if self.multiline:
            self.input1.setText(text)
        else:
            self.input1.setText(text)
        self.noSignal = False
        if signal is True:
            self.editingFinished.emit()

    def text(self) -> str:
        """ Return the text. """
        text = self.input1.text()
        return text.replace("\\n", "\n")

    def get(self) -> str:
        import ast
        """ Get the value (used for the Linkable parent class). """
        if self.allow_literal_decoding:
            try:
                return ast.literal_eval(self.text())
            except ValueError:
                return self.text()
        return self.text()

    def set(self, value: str):
        """ Set the value (used for the Linkable parent class). """
        self.setText(str(value))

    def getSerialized(self) -> str:
        """ Serialize the value (used for the Linkable parent class). """
        return "\"" + str(self.get()) + "\""


class NumberWidget(QtWidgets.QWidget, Linkable):
    editingFinished = QtCore.Signal()
    noSignal = False

    def __init__(self, layout: QtWidgets.QLayout, text: str, min: float = None, use_float: bool = True):
        """ A spin box with a label next to it.

        Args:
            layout: the layout to which to add the widget
            text: the label text
            min: the minimum value of the spin box
            use_float: whether to use a float spin box or an int spin box.
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel(text)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.type = float if use_float else int
        if use_float is False:
            self.input1 = QtWidgets.QSpinBox()
        else:
            self.input1 = QtWidgets.QDoubleSpinBox()
        if min is not None:
            self.input1.setMinimum(min)
        self.input1.valueChanged.connect(self.valueChangeEvent)
        self.layout.addWidget(self.input1)

    def valueChangeEvent(self):
        """ When the value of the spin box changes. """
        if not self.noSignal:
            self.editingFinished.emit()

    def setLabel(self, text: str):
        """ Set the text label. """
        self.label.setLabel(text)

    def setValue(self, text: float, signal=False):
        """ Set the value of the spin box. """
        self.noSignal = True
        self.input1.setValue(text)
        self.noSignal = False
        if signal is True:
            self.editingFinished.emit()

    def value(self) -> float:
        """ Get the value of the spin box. """
        text = self.input1.value()
        return text

    def get(self) -> float:
        """ Get the value (used for the Linkable parent class). """
        return self.value()

    def set(self, value: float):
        """ Set the value (used for the Linkable parent class). """
        self.setValue(value)

    def getSerialized(self) -> str:
        """ Serialize the value (used for the Linkable parent class). """
        return str(self.get())


class ComboWidget(QtWidgets.QWidget, Linkable):
    editingFinished = QtCore.Signal()
    noSignal = False

    def __init__(self, layout: QtWidgets.QLayout, text: str, values: Sequence):
        """ A combo box widget with a label.

        Args:
            layout: the layout to which to add the widget
            text: the label text
            values: the possible values of the combo box
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel(text)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.values = values

        self.input1 = QtWidgets.QComboBox()
        self.input1.addItems(values)
        self.layout.addWidget(self.input1)

        self.input1.currentIndexChanged.connect(self.valueChangeEvent)
        self.layout.addWidget(self.input1)

    def valueChangeEvent(self):
        """ Called when the value has changed. """
        if not self.noSignal:
            self.editingFinished.emit()

    def setLabel(self, text: str):
        """ Set the text of the label. """
        self.label.setLabel(text)

    def setText(self, text: str, signal=False):
        """ Set the value of the combo box. """
        self.noSignal = True
        index = self.values.index(text)
        self.input1.setCurrentIndex(index)
        self.noSignal = False
        if signal is True:
            self.editingFinished.emit()

    def text(self) -> str:
        """ Get the value of the combo box. """
        index = self.input1.currentIndex()
        return self.values[index]

    def get(self) -> str:
        """ Get the value (used for the Linkable parent class). """
        return self.text()

    def set(self, value: str):
        """ Set the value (used for the Linkable parent class). """
        self.setText(value)

    def getSerialized(self) -> str:
        """ Serialize the value (used for the Linkable parent class). """
        return "\"" + str(self.get()) + "\""


class CheckWidget(QtWidgets.QWidget, Linkable):
    editingFinished = QtCore.Signal()
    stateChanged = QtCore.Signal(int)
    noSignal = False

    def __init__(self, layout: QtWidgets.QLabel, text: str):
        """ A widget that contains a checkbox with a label.

        Args:
            layout: the layout to which to add the widget
            text: the label text
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel(text)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.input1 = QtWidgets.QCheckBox()
        self.input1.setTristate(False)
        self.input1.stateChanged.connect(self.onStateChanged)
        self.layout.addWidget(self.input1)

    def onStateChanged(self):
        """ When the state of the checkbox changes. """
        if not self.noSignal:
            self.stateChanged.emit(self.input1.isChecked())
            self.editingFinished.emit()

    def setChecked(self, state: bool, signal=False):
        """ Set the value of the check box. """
        self.noSignal = True
        self.input1.setChecked(state)
        self.noSignal = False
        if signal:
            self.stateChanged.emit(self.input1.isChecked())
            self.editingFinished.emit()

    def isChecked(self) -> bool:
        """ Get the value of the checkbox. """
        return self.input1.isChecked()

    def get(self) -> bool:
        """ Set the value (used for the Linkable parent class). """
        return self.isChecked()

    def set(self, value: bool):
        """ Get the value (used for the Linkable parent class). """
        self.setChecked(value)

    def getSerialized(self) -> str:
        """ Serialize the value (used for the Linkable parent class). """
        return "True" if self.get() else "False"


class RadioWidget(QtWidgets.QWidget):
    stateChanged = QtCore.Signal(int, str)
    noSignal = False

    def __init__(self, layout: QtWidgets.QLayout, texts: Sequence[str]):
        """ A group of radio buttons.

        Args:
            layout: the layout to which to add the widget
            texts: the text label
        """
        QtWidgets.QWidget.__init__(self)
        layout.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.radio_buttons = []

        self.texts = texts

        for name in texts:
            radio = QtWidgets.QRadioButton(name)
            radio.toggled.connect(self.onToggled)
            self.layout.addWidget(radio)
            self.radio_buttons.append(radio)
        self.radio_buttons[0].setChecked(True)

    def onToggled(self, checked: int):
        """ Called when a radio button is toggled. """
        if checked:
            self.checked = np.argmax([radio.isChecked() for radio in self.radio_buttons])
            if not self.noSignal:
                self.stateChanged.emit(self.checked, self.texts[self.checked])

    def setState(self, state: int):
        """ Set the state of the widget. """
        self.noSignal = True
        for index, radio in enumerate(self.radio_buttons):
            radio.setChecked(state == index)
        self.checked = state
        self.noSignal = False

    def getState(self) -> int:
        """ Get the state of the widget. """
        return self.checked


class QColorWidget(QtWidgets.QWidget, Linkable):
    valueChanged = QtCore.Signal(str)

    def __init__(self, layout: QtWidgets.QLayout, text: str = None, value: str = None):
        """ A colored button what acts as an color input.

        Args:
            layout: the layout to which to add the widget
            text: the label text
            value: the value of the color widget
        """
        super().__init__()
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self)

        if text is not None:
            self.label = QtWidgets.QLabel(text)
            self.layout.addWidget(self.label)

        self.button = QtWidgets.QPushButton()
        self.layout.addWidget(self.button)

        self.button.clicked.connect(self.OpenDialog)
        # default value for the color
        if value is None:
            value = "#FF0000FF"
        # set the color
        self.setColor(value)

        self.editingFinished = self.valueChanged

    def changeEvent(self, event):
        """ When the widget is enabled. """
        if event.type() == QtCore.QEvent.EnabledChange:
            if not self.isEnabled():
                self.button.setStyleSheet("background-color: #f0f0f0;")
            else:
                self.setColor(self.color)

    def OpenDialog(self):
        """ Open a color chooser dialog. """
        # get new color from color picker
        self.current_color = QtGui.QColor(*tuple(int(x) for x in mpl.colors.to_rgba_array(self.getColor())[0] * 255))
        self.dialog = QtWidgets.QColorDialog(self.current_color, self.parent())
        self.dialog.setOptions(QtWidgets.QColorDialog.ShowAlphaChannel)
        for index, color in enumerate(plt.rcParams['axes.prop_cycle'].by_key()['color']):
            self.dialog.setCustomColor(index, QtGui.QColor(color))
        self.dialog.open(self.dialog_finished)
        self.dialog.currentColorChanged.connect(self.dialog_changed)
        self.dialog.rejected.connect(self.dialog_rejected)

    def dialog_rejected(self):
        """ Called when the dialog is cancelled. """
        color = self.current_color
        color = color.name() + f"{color.alpha():002x}"
        self.setColor(color)
        self.valueChanged.emit(self.color)

    def dialog_changed(self):
        """ Called when the value in the dialog changes. """
        color = self.dialog.currentColor()
        # if a color is set, apply it
        if color.isValid():
            color = color.name() + f"{color.alpha():002x}"
            self.setColor(color)
            self.valueChanged.emit(self.color)

    def dialog_finished(self):
        """ Called when the dialog is finished with a click on 'ok'. """
        color = self.dialog.selectedColor()
        self.dialog = None
        # if a color is set, apply it
        if color.isValid():
            color = color.name() + f"{color.alpha():002x}"
            self.setColor(color)
            self.valueChanged.emit(self.color)

    def setColor(self, value: str):
        """ Set the color. """
        # display and save the new color
        if value is None:
            value = "#FF0000FF"
        self.button.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        if len(value) == 9:
            self.button.setStyleSheet("background-color: rgba(%d, %d, %d, %d%%);" % (
            int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), int(value[7:], 16) * 100 / 255))
        else:
            self.button.setStyleSheet(f"background-color: {value};")
        self.color = value

    def getColor(self) -> str:
        """ Get the color value. """
        # return the color
        return self.color

    def get(self):
        """ Get the value (used for the Linkable parent class). """
        return self.getColor()

    def set(self, value):
        """ Set the value (used for the Linkable parent class). """
        try:
            if len(value) == 4:
                self.setColor(mpl.colors.to_hex(value) + f"{int(value[-1] * 255):02X}")
            else:
                self.setColor(mpl.colors.to_hex(value))
        except ValueError:
            self.setColor(None)

    def getSerialized(self) -> str:
        """ Serialize the value (used for the Linkable parent class). """
        return "\"" + self.color + "\""
