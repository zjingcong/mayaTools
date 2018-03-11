
import maya.cmds as cmds
import mtoa.core as core

import traceback
from PySide import QtCore
from PySide import QtGui
from shiboken import wrapInstance
import maya.OpenMayaUI as omui

import os


houdini_assets_filetype = ('.hda', '.hdanc')
alembic_filetype = ('.abc')


def maya_main_window():
    '''
    Return the Maya main window widget as a Python object
    '''
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtGui.QWidget)


class HouPopImportUi(QtGui.QDialog):
    def __init__(self, parent=maya_main_window()):
        super(HouPopImportUi, self).__init__(parent)
        self.import_opacity = False
        self.import_color = True
        self.asset_path = ''
        self.color_channel = 'baseColor'

    def create(self):
        '''
        Set up the UI prior to display
        '''
        self.setWindowTitle('Houdini Import With Arnold Shader')
        self.setWindowFlags(QtCore.Qt.Tool)
        self.create_controls()
        self.create_layout()
        self.resize(480, 60)

    def create_controls(self):
        '''
        Create the widgets for the dialog
        '''
        self.checkbox_opacity = self.create_checkbox('&Import Opacity', self.on_checkbox_toggled_opacity)
        self.checkbox_color = self.create_checkbox('&Import Color', self.on_checkbox_toggled_color)
        self.browse_button = self.create_toolbutton(self.on_button_browse)
        self.push_button = self.create_pushbutton('&OK', self.on_button_pressed)
        self.line_edit = self.create_lineedit('', self.on_lineedit_changed)
        self.combobox = self.create_combobox(['baseColor', 'emitColor'], self.on_combobox_activated)
        self.color_label = self.create_label('Color Channel')
        self.path_label = self.create_label('Asset Path')

        # init state
        self.checkbox_color.setChecked(1)
        self.combobox.setCurrentIndex(self.combobox.findText(self.color_channel))

    def create_layout(self):
        '''
        Create the layouts and add widgets
        '''
        lineedit_layout = QtGui.QHBoxLayout()
        lineedit_layout.setContentsMargins(2, 2, 2, 2)
        lineedit_layout.addWidget(self.path_label)
        lineedit_layout.addWidget(self.line_edit)
        lineedit_layout.addWidget(self.browse_button)

        combobox_layout = QtGui.QHBoxLayout()
        combobox_layout.setContentsMargins(2, 2, 2, 2)
        combobox_layout.addWidget(self.checkbox_color)
        combobox_layout.addWidget(self.color_label)
        combobox_layout.addWidget(self.combobox)
        combobox_layout.addStretch(1)

        checkbox_layout = QtGui.QHBoxLayout()
        checkbox_layout.setContentsMargins(2, 2, 2, 2)
        checkbox_layout.addWidget(self.checkbox_opacity)

        button_layout = QtGui.QHBoxLayout()
        button_layout.setContentsMargins(2, 2, 2, 2)
        self.push_button.setMaximumWidth(60)
        button_layout.addWidget(self.push_button)
        button_layout.setAlignment(QtCore.Qt.AlignCenter)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)

        main_layout.addLayout(lineedit_layout)
        main_layout.addLayout(combobox_layout)
        main_layout.addLayout(checkbox_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def create_label(self, text):
        label = QtGui.QLabel(text)
        return label

    def create_pushbutton(self, text, member):
        button = QtGui.QPushButton(text)
        button.clicked.connect(member)
        return button

    def create_checkbox(self, text, member):
        checkbox = QtGui.QCheckBox(text)
        checkbox.toggled.connect(member)
        return checkbox

    def create_toolbutton(self, member):
        button = QtGui.QToolButton()
        button.setText('...')
        button.clicked.connect(member)
        return button

    def create_lineedit(self, text, member):
        lineedit = QtGui.QLineEdit(text)
        lineedit.textChanged.connect(member)
        return lineedit

    def create_combobox(self, text, member):
        combobox = QtGui.QComboBox()
        for t in text:
            combobox.addItem(t)
        combobox.activated.connect(member)
        return combobox

    # --------------------------------------------------------------------------
    # SLOTS
    # --------------------------------------------------------------------------

    def on_combobox_activated(self):
        sender = self.sender()
        current_text = sender.currentText()
        self.color_channel = current_text

    def on_button_browse(self):
        filename, filter = QtGui.QFileDialog.getOpenFileName(self)
        if filename:
            self.line_edit.setText(filename)

    def on_lineedit_changed(self):
        self.asset_path = self.line_edit.text()

    def on_checkbox_toggled_opacity(self):
        sender = self.sender()
        if sender.isChecked():
            self.import_opacity = True
        else:
            self.import_opacity = False

    def on_checkbox_toggled_color(self):
        sender = self.sender()
        if sender.isChecked():
            self.import_color = True
            self.combobox.setDisabled(0)
        else:
            self.import_color = False
            self.combobox.setDisabled(1)

    def on_button_pressed(self):
        self.do_import()
        self.close()

    # --------------------------------------------------------------------------
    # IMPORT
    # --------------------------------------------------------------------------

    def do_import(self):
        if self.asset_path == '':
            return
        if self.asset_path.lower().endswith(houdini_assets_filetype):
            self.import_particles()
        elif self.asset_path.lower().endswith(alembic_filetype):
            self.import_abcgeom()

    def import_particles(self):
        # load houdini assets
        asset_name = os.path.split(self.asset_path)[-1].split('.')[0]
        asset = cmds.houdiniAsset(loadAsset=[self.asset_path, "Object/{}".format(asset_name)])

        # create shader
        surface_name = '{}_particles'.format(asset)
        # create surface shader
        surface_name = core.createArnoldNode('aiStandardSurface', name=surface_name)
        # assign shader
        cmds.sets(asset, edit=True, forceElement='{}SG'.format(surface_name))

        # particle color
        if self.import_color:
            color_name = '{}_rgbPP'.format(surface_name)
            # import particle color
            color_name = core.createArnoldNode('aiUserDataColor', name=color_name)
            cmds.setAttr('{}.colorAttrName'.format(color_name), 'rgbPP', type='string')
            if self.color_channel == 'baseColor':
                cmds.connectAttr('{}.outColor'.format(color_name), '{}.baseColor'.format(surface_name))
            elif self.color_channel == 'emitColor':
                cmds.connectAttr('{}.outColor'.format(color_name), '{}.emissionColor'.format(surface_name))
                cmds.setAttr('{}.emission'.format(surface_name), 1)

        # particle opacity
        if self.import_opacity:
            opacity_name = '{}_opacityPP'.format(surface_name)
            # disable opaque
            children = cmds.listRelatives(asset, allDescendents=True)
            for child in children:
                if cmds.nodeType(child) == 'nParticle':
                    cmds.setAttr('{}.aiOpaque'.format(child), 0)
            # import opacity
            opacity_name = core.createArnoldNode('aiUserDataFloat', name=opacity_name)
            cmds.setAttr('{}.attribute'.format(opacity_name), 'opacityPP', type='string')
            cmds.connectAttr('{}.outTransparency'.format(opacity_name), '{}.opacity'.format(surface_name))

    def import_abcgeom(self):
        # import alembic
        alembic_node = cmds.AbcImport(self.asset_path, mode="import", recreateAllColorSets=True)
        trans_node = cmds.listConnections(alembic_node, type="mesh")[0]
        mesh_node = cmds.listRelatives(trans_node, type="mesh")[0]
        # need test if all color sets can be imported from aiUserDataColor
        cmds.setAttr('{}.allColorSets'.format(alembic_node), 1)
        current_color = cmds.polyColorSet(trans_node, query=True, currentColorSet=True)[0]  # need to test: allColorSet=True

        # create shader
        surface_name = '{}_geom'.format(trans_node)
        # create surface shader
        surface_name = core.createArnoldNode('aiStandardSurface', name=surface_name)
        cmds.sets(trans_node, edit=True, forceElement='{}SG'.format(surface_name))

        # import color
        if self.import_color:
            cmds.setAttr('{trans}|{mesh}.aiExportColors'.format(trans=trans_node, mesh=mesh_node), 1)
            color_name = '{0}_{1}'.format(surface_name, current_color)
            # import particle color
            color_name = core.createArnoldNode('aiUserDataColor', name=color_name)
            cmds.setAttr('{}.colorAttrName'.format(color_name), current_color, type='string')
            if self.color_channel == 'baseColor':
                cmds.connectAttr('{}.outColor'.format(color_name), '{}.baseColor'.format(surface_name))
            elif self.color_channel == 'emitColor':
                cmds.connectAttr('{}.outColor'.format(color_name), '{}.emissionColor'.format(surface_name))
                cmds.setAttr('{}.emission'.format(surface_name), 1)

        # set opacity
        if self.import_opacity:
            cmds.setAttr('{trans}|{mesh}.aiOpaque'.format(trans=trans_node, mesh=mesh_node), 0)


if __name__ == "__main__":
    # Make sure the UI is deleted before recreating
    try:
        houpopimport_ui.deleteLater()
    except:
        pass

    # Create minimal UI object
    houpopimport_ui = HouPopImportUi()

    # Delete the UI if errors occur to avoid causing winEvent
    try:
        houpopimport_ui.create()
        houpopimport_ui.show()
    except:
        houpopimport_ui.deleteLater()
        traceback.print_exc()
