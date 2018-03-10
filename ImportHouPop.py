import maya.cmds as cmds
import maya.mel as mel
import mtoa.core as core
import traceback
from PySide import QtCore
from PySide import QtGui
from shiboken import wrapInstance
import maya.OpenMayaUI as omui


def maya_main_window():
    '''
    Return the Maya main window widget as a Python object
    '''
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtGui.QWidget)


class HouPopImportUi(QtGui.QDialog):
    test_signal = QtCore.Signal()

    def __init__(self, parent=maya_main_window()):
        super(HouPopImportUi, self).__init__(parent)
        self.importOpacity = False
        self.asset_path = ''

    def create(self):
        '''
        Set up the UI prior to display
        '''
        self.setWindowTitle('Houdini Pop Import')
        self.setWindowFlags(QtCore.Qt.Tool)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):
        '''
        Create the widgets for the dialog
        '''
        self.push_button = QtGui.QPushButton('OK')
        self.checkbox_opacity = QtGui.QCheckBox("Import Opacity")
        self.line_edit = QtGui.QLineEdit("filename")

    def create_layout(self):
        '''
        Create the layouts and add widgets
        '''
        check_box_layout = QtGui.QHBoxLayout()
        check_box_layout.setContentsMargins(2, 2, 2, 2)
        check_box_layout.addWidget(self.checkbox_opacity)
        # check_box_layout.addWidget(self.check_box_02)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)

        main_layout.addLayout(check_box_layout)
        main_layout.addWidget(self.line_edit)
        main_layout.addWidget(self.push_button)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def create_connections(self):
        self.push_button.clicked.connect(self.on_button_pressed)
        self.checkbox_opacity.toggled.connect(self.on_checkbox_toggled)
        self.line_edit.textChanged.connect(self.on_text_changed)

    # def create_button(self, text, member):
    #     button = QtGui.QPushButton(text)
    #     button.clicked.connect(member)
    #     return button
    #
    # def create_checkbox(self, text, member):
    #     checkbox = QtGui.QCheckBox(text)
    #     checkbox.toggled.connect(member)
    #     return checkbox
    #
    # def create_lineedit(self, text, member):
    #     lineedit = QtGui.QLineEdit(text)
    #     lineedit.textChanged.connect(member)
    #     return lineedit

    # --------------------------------------------------------------------------
    # SLOTS
    # --------------------------------------------------------------------------
    def on_button_pressed(self):
        asset_name = self.asset_path.split('/')[-1].split('.')[0]
        # load houdini assets
        asset = cmds.houdiniAsset(loadAsset=[self.asset_path, "Object/{}".format(asset_name)])

        # create shader
        surface_name = '{}_particles'.format(asset)
        # create surface shader
        surface_name = core.createArnoldNode('aiStandardSurface', name=surface_name)

        # assign shader
        cmds.select(asset)
        cmds.hyperShade(assign='{}'.format(surface_name))

        # particle color
        color_name = '{}_rgbPP'.format(surface_name)
        # import particle color
        core.createArnoldNode('aiUserDataColor', name=color_name)
        cmds.setAttr('{}.colorAttrName'.format(color_name), 'rgbPP', type='string')
        cmds.connectAttr('{}.outColor'.format(color_name), '{}.baseColor'.format(surface_name))

        # particle opacity
        if self.importOpacity:
            opacity_name = '{}_opacityPP'.format(surface_name)
            # disable opaque
            children = cmds.listRelatives(asset, allDescendents=True)
            for child in children:
                if cmds.nodeType(child) == 'nParticle':
                    cmds.setAttr('{}.aiOpaque'.format(child), 0)
            # import opacity
            core.createArnoldNode('aiUserDataFloat', name=opacity_name)
            cmds.setAttr('{}.attribute'.format(opacity_name), 'opacityPP', type='string')
            cmds.connectAttr('{}.outTransparency'.format(opacity_name), '{}.opacity'.format(surface_name))

    def on_checkbox_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            self.importOpacity = True
        else:
            self.importOpacity = False

    def on_text_changed(self):
        text = self.line_edit.text()
        self.asset_path = text


if __name__ == "__main__":
    # Make sure the UI is deleted before recreating
    try:
        houpopimport_ui.deleteLater()
    except:
        pass

    # Create minimal UI object
    houpopimport_ui = HouPopImportUi()

    # Delete the UI if errors occur to avoid causing winEvent
    # and event errors (in Maya 2014)
    try:
        houpopimport_ui.create()
        houpopimport_ui.show()
    except:
        houpopimport_ui.deleteLater()
        traceback.print_exc()
