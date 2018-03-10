
import maya.cmds as cmds
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
    def __init__(self, parent=maya_main_window()):
        super(HouPopImportUi, self).__init__(parent)
        self.importOpacity = False
        self.asset_path = ''
        self.color_channel = 'baseColor'

    def create(self):
        '''
        Set up the UI prior to display
        '''
        self.setWindowTitle('Houdini Pop Import')
        self.setWindowFlags(QtCore.Qt.Tool)
        self.create_controls()
        self.create_layout()
        self.resize(480, 60)

    def create_controls(self):
        '''
        Create the widgets for the dialog
        '''
        self.checkbox_opacity = self.create_checkbox('&Import Opacity', self.on_checkbox_toggled)
        self.browse_button = self.create_toolbutton('...', self.on_button_browse)
        self.push_button = self.create_pushbutton('&OK', self.on_button_pressed)
        self.line_edit = self.create_lineedit(QtCore.QDir.currentPath(), self.on_lineedit_changed)
        self.combobox = self.create_combobox(['baseColor', 'emitColor'], self.on_combobox_activated)
        self.label = self.create_label()

    def create_layout(self):
        '''
        Create the layouts and add widgets
        '''
        check_box_layout = QtGui.QHBoxLayout()
        check_box_layout.setContentsMargins(2, 2, 2, 2)
        check_box_layout.addWidget(self.checkbox_opacity)

        line_edit_layout = QtGui.QHBoxLayout()
        line_edit_layout.setContentsMargins(2, 2, 2, 2)
        line_edit_layout.addWidget(self.line_edit)
        line_edit_layout.addWidget(self.browse_button)

        combobox_layout = QtGui.QHBoxLayout()
        combobox_layout.setContentsMargins(2, 2, 2, 2)
        combobox_layout.addWidget(self.label)
        combobox_layout.addWidget(self.combobox)
        combobox_layout.addStretch(1)

        button_layout = QtGui.QHBoxLayout()
        button_layout.setContentsMargins(2, 2, 2, 2)
        self.push_button.setMaximumWidth(60)
        button_layout.addWidget(self.push_button)
        button_layout.setAlignment(QtCore.Qt.AlignCenter)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)

        main_layout.addLayout(check_box_layout)
        main_layout.addLayout(line_edit_layout)
        main_layout.addLayout(combobox_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def create_label(self):
        label = QtGui.QLabel('Color Channel')
        return label

    def create_pushbutton(self, text, member):
        button = QtGui.QPushButton(text)
        button.clicked.connect(member)
        return button

    def create_checkbox(self, text, member):
        checkbox = QtGui.QCheckBox(text)
        checkbox.toggled.connect(member)
        return checkbox

    def create_toolbutton(self, text, member):
        button = QtGui.QToolButton()
        button.setText(text)
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
        combobox.setCurrentIndex(combobox.findText(self.color_channel))
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
            self.asset_path = filename
            self.line_edit.setText(self.asset_path)

    def on_lineedit_changed(self):
        self.asset_path = self.line_edit.text()
        print self.asset_path

    def on_button_pressed(self):
        if self.asset_path == '':
            self.close()
            return

        asset_name = self.asset_path.split('/')[-1].split('.')[0]
        # load houdini assets
        asset = cmds.houdiniAsset(loadAsset=[self.asset_path, "Object/{}".format(asset_name)])

        # create shader
        surface_name = '{}_particles'.format(asset)
        # create surface shader
        surface_name = core.createArnoldNode('aiStandardSurface', name=surface_name)

        # assign shader
        cmds.sets(asset, edit=True, forceElement='{}SG'.format(surface_name))

        # particle color
        color_name = '{}_rgbPP'.format(surface_name)
        # import particle color
        core.createArnoldNode('aiUserDataColor', name=color_name)
        cmds.setAttr('{}.colorAttrName'.format(color_name), 'rgbPP', type='string')
        if self.color_channel == 'baseColor':
            cmds.connectAttr('{}.outColor'.format(color_name), '{}.baseColor'.format(surface_name))
        elif self.color_channel == 'emitColor':
            cmds.connectAttr('{}.outColor'.format(color_name), '{}.emissionColor'.format(surface_name))
            cmds.setAttr('{}.emission'.format(surface_name), 1)

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

        self.close()

    def on_checkbox_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            self.importOpacity = True
        else:
            self.importOpacity = False


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
