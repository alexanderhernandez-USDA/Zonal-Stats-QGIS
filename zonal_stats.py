# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ZonalStats
                                 A QGIS plugin
 Calculate indices and extract zonal statistics
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-10-11
        git sha              : $Format:%H$
        copyright            : (C) 2024 by USDA ARS FRR
        email                : kaden.patten@usda.gov
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import Qgis, QgsTask, QgsApplication
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, pyqtSignal, QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QFileInfo, Qt
from qgis.PyQt.QtGui import QIcon, QPixmap, QGuiApplication
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox, QGraphicsScene, QFrame, QGraphicsPixmapItem, QListWidget, QListWidgetItem, QApplication
import subprocess, platform

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .zonal_stats_dialog import ZonalStatsDialog
import os.path

def showDialog(window_title, dialog_text, icon_level):
    dialog = QMessageBox()
    dialog.setSizeGripEnabled(True)
    dialog.setWindowTitle(window_title)
    dialog.setText(dialog_text)
    dialog.setIcon(icon_level)
    dialog.exec_()

class ZonalStats(QObject):
    finished_signal = pyqtSignal(int,object)
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        super().__init__()
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ZonalStats_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Zonal Statistics')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.tm = QgsApplication.taskManager()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ZonalStats', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def read_config(self,conf):
        vegIndices = []
        if not os.path.exists(conf):
            return vegIndices
        with open(conf,"r") as f:
            configs = f.read().split("\n")
        for i in configs:
            if i=="":
                continue
            if i.strip()[0]=="#":
                continue
            if i[0] == "[" and i[-1]=="]":
                name = i[1:-1]
                desc = ""
                calc = ""
            elif "desc" in i:
                desc = i.split(":")[-1].strip()
            elif "calc" in i:
                calc = i.split(':')[-1].strip()
                vegIndices.append(f"{name}:: {desc}")
        return vegIndices

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/zonal_stats/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Run Zonal Statistics'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        #self.first_start = False

        self.location = os.path.dirname(__file__)
        if platform.system() == "Windows":
            self.exec = os.path.join(self.location,"zsenv/Scripts/python.exe")
        else:
            self.exec = os.path.join(self.location,"zsenv/bin/python")
        self.script = os.path.join(self.location,"zonal_stats_3.py")
        self.log = os.path.join(self.location,"zs_log.txt")

        self.dlg = ZonalStatsDialog()

        self.vegIndices = self.read_config(os.path.join(self.location,"indices.conf"))

        self.use_points = False
        self.use_buffer = False
        self.threads = 1
        self.calc = "NONE"
        self.buffer_type = "CIRCLE"
        self.buffer_size = 1
        self.save_output = False
        self.uid = "id"
        self.band_order = ""
        self.img_folder = ""
        self.input_gpkg = ""
        self.output_gpkg = ""
        
        self.dlg.dem_widget.hide()
        self.dlg.index_widget.hide()
        self.dlg.band_order.show()
        self.dlg.in_band_order.show()
        self.dlg.use_buffer.hide()
        self.dlg.buffer_type.hide()
        self.dlg.label_buffer.hide()
        self.dlg.buffer_size_widget.hide()
        self.dlg.label_out.hide()
        self.dlg.output_folder.hide()
        self.dlg.output_button.hide()

        for i in self.vegIndices:
            item = QListWidgetItem()
            item.setText(QApplication.translate("Dialog", str(i), None))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.dlg.input_indices_list.addItem(item)

        self.dlg.input_indices_list.itemChanged.connect(lambda item: self.check_index_items())

        self.dlg.mGroupBox.collapsedStateChanged.connect(self.onSelectIndexCalc)

        self.dlg.input_folder.textChanged.connect(self.onInputFolderChanged)
        self.dlg.input_button.clicked.connect(self.onSelectPhotoFolder)
        self.dlg.input_gpkg.textChanged.connect(self.onInputGPKGChanged)
        self.dlg.input_gpkg_button.clicked.connect(self.onSelectGPKG)
        self.dlg.output_gpkg.textChanged.connect(self.onOutputGPKGChanged)
        self.dlg.output_gpkg_button.clicked.connect(self.onSelectOutputGPKG)
        self.dlg.input_dem.textChanged.connect(self.onDEMChange)
        self.dlg.dem_button.clicked.connect(self.onSelectDEM)
        self.dlg.dem_widget.hide()
        self.dlg.index_widget.hide()
        self.dlg.close_button.clicked.connect(self.onClose)
        self.dlg.ok_button.clicked.connect(self.onExecute)

        self.dlg.index_calculation.currentIndexChanged.connect(self.onSelectIndexCalc)
        self.dlg.in_band_order.textChanged.connect(self.onBandOrderChanged)
        self.dlg.use_points.stateChanged.connect(self.onPointsChanged)
        self.dlg.use_buffer.stateChanged.connect(self.onUseBufferChanged)
        self.dlg.save_multilayer.stateChanged.connect(self.onSaveOutputChanged)
        self.dlg.output_folder.textChanged.connect(self.onOutputFolderChanged)
        self.dlg.output_button.clicked.connect(self.onSelectOutputFolder)
        self.dlg.threads.textChanged.connect(self.onThreadsChanged)
        self.dlg.uid.textChanged.connect(self.onUIDChanged)
        self.dlg.buffer_type.currentIndexChanged.connect(self.onBufferTypeChanged)
        self.dlg.buffer_size.textChanged.connect(self.onBufferSizeChanged)
        self.dlg.run_all.stateChanged.connect(self.onRunAllChanged)

        #self.setupWelcomePhoto()

        


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Zonal Statistics'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ZonalStatsDialog()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    # UI Functions
    def onInputFolderChanged(self):
        self.img_folder = self.dlg.input_folder.text()
        #self.onClearAdjacentPhotos()
        self.dlg.progress_bar.setValue(0)

    def onSelectPhotoFolder(self):
        folder = QFileDialog.getExistingDirectory(self.dlg, "Select folder ")
        # if user do not select any folder, then don't change folder_name
        if len(folder) > 1:
            self.dlg.input_folder.setText(folder)

    def onOutputFolderChanged(self):
        self.out_folder = self.dlg.output_folder.text()
        
    def onSelectOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(self.dlg, "Select folder ")
        if len(folder) > 1:
            self.dlg.output_folder.setText(folder)

    def onSelectIndexCalc(self):
        method_index = self.dlg.index_calculation.currentIndex()
        if method_index == 0:
            self.dlg.dem_widget.hide()
            self.dlg.index_widget.hide()
            self.dlg.band_order.show()
            self.dlg.in_band_order.show()
            self.calc = "NONE"
        elif method_index == 1:
            self.dlg.dem_widget.hide()
            self.dlg.index_widget.hide()
            self.dlg.band_order.hide()
            self.dlg.in_band_order.hide()
            self.calc = "VOLUME"
        elif method_index == 2:
            self.dlg.input_dem_label.setText("Reference DEM")
            self.dlg.dem_widget.show()
            self.dlg.index_widget.hide()
            self.dlg.band_order.hide()
            self.dlg.in_band_order.hide()
            self.calc = "VOLUME_REF"
        else:
            self.dlg.dem_widget.hide()
            self.dlg.index_widget.show()
            self.dlg.band_order.show()
            self.dlg.in_band_order.show()
            self.calc = "INDICES"

    def onPointsChanged(self):
        self.use_points = self.dlg.use_points.checkState()
        if self.use_points:
            self.dlg.use_buffer.show()
        else:
            self.dlg.use_buffer.hide()
            self.dlg.buffer_type.hide()
            self.dlg.label_buffer.hide()
            self.use_buffer = False
            self.dlg.use_buffer.setCheckState(False)

    def onUseBufferChanged(self):
        self.use_buffer = self.dlg.use_buffer.checkState()
        if self.use_buffer:
            self.dlg.buffer_type.show()
            self.dlg.label_buffer.show()
            self.dlg.buffer_size_widget.show()
        else:
            self.dlg.buffer_type.hide()
            self.dlg.label_buffer.hide()
            self.dlg.buffer_size_widget.hide()
    
    def onBufferTypeChanged(self):
        if self.dlg.buffer_type.currentIndex() == 0:
            self.buffer_type = "CIRCLE"
        else:
            self.buffer_type = "SQUARE"

    def onBufferSizeChanged(self):
        if self.dlg.buffer_size.text() == "":
            self.buffer_size = 1
        else:
            try:
                self.buffer_size = float(self.dlg.buffer_size.text())
            except:
                self.dlg.buffer_size.setText("")
                self.buffer_size = 1

    def onSaveOutputChanged(self):
        self.save_output = self.dlg.save_multilayer.checkState()
        if self.save_output:
            self.dlg.label_out.show()
            self.dlg.output_folder.show()
            self.dlg.output_button.show()
        else:
            self.dlg.label_out.hide()
            self.dlg.output_folder.hide()
            self.dlg.output_button.hide()

    def onThreadsChanged(self):
        if self.dlg.threads.text() == "":
            self.threads = 1
        else:
            try:
                self.threads = int(self.dlg.threads.text())
                if self.threads <1:
                    self.threads = 1
            except:
                self.dlg.threads.setText("")
                self.threads = 1

    def onUIDChanged(self):
        self.uid = self.dlg.uid.text()
        if self.uid == "":
            self.uid = "id"

    def onBandOrderChanged(self):
        if self.dlg.in_band_order.text() == "":
            self.band_order = "red,green,blue,rededge,nir"
        else:
            self.band_order = self.dlg.in_band_order.text()

    def check_index_items(self):
        self.indices = []
        for i in range(self.dlg.input_indices_list.count()):
            item = self.dlg.input_indices_list.item(i)
            if item.checkState():
                self.indices.append(item.text().split("::")[0])
        self.indices = ",".join(self.indices)

    def onRunAllChanged(self):
        if self.dlg.run_all.checkState():
            self.indices = "ALL"
            self.dlg.input_indices_list.hide()
        else:
            self.dlg.input_indices_list.show()
            self.check_index_items()

    def onDEMChange(self):
        self.dem_path = self.dlg.input_dem.text()

    def onSelectDEM(self):
        filename, _filter = QFileDialog.getOpenFileName(self.dlg, "Select DEM file ", "", '*.tif')
        # prevent assigning DEM to ""
        if len(filename) > 1:
            self.dlg.input_dem.setText(filename)

    def onSelectGPKG(self):
        filename, _filter = QFileDialog.getOpenFileName(self.dlg, "Select GPKG file ", "", '*.gpkg')
        # prevent assigning DEM to ""
        if len(filename) > 1:
            self.dlg.input_gpkg.setText(filename)

    def onInputGPKGChanged(self):
        self.input_gpkg = self.dlg.input_gpkg.text()


    def onSelectOutputGPKG(self):
        filename, _filter = QFileDialog.getOpenFileName(self.dlg, "Select GPKG file ", "", '*.gpkg')
        # prevent assigning DEM to ""
        if len(filename) > 1:
            self.dlg.output_gpkg.setText(filename)

    def onOutputGPKGChanged(self):
        self.output_gpkg = self.dlg.output_gpkg.text()

    #def onCancel(self):
    #    """Cancel task execution."""
    #    try:
    #        self.alt_task.cancel()
    #        return 0
    #    except Exception:
    #        return 1

    def onClose(self):
        """Close plugin."""
        self.dlg.close()

    def onExecute(self):
        if self.img_folder == "" or not os.path.isdir(self.img_folder):
            showDialog(window_title="Error: Invalid Input",
                       dialog_text="Please enter a valid input folder",
                       icon_level=QMessageBox.Critical)
            return
        if self.input_gpkg == "" or not os.path.isfile(self.input_gpkg):
            showDialog(window_title="Error: Invalid Input",
                       dialog_text="Please enter a valid input geopackage",
                       icon_level=QMessageBox.Critical)
            return
        if self.output_gpkg == "":
            showDialog(window_title="Error: Invalid Output",
                       dialog_text="Please enter a valid output geopackage",
                       icon_level=QMessageBox.Critical)
            return

        args = [self.exec, self.script]
        args.append("-t")
        args.append(str(self.threads))
        args.append("-u")
        args.append(self.uid)

        if self.use_points:
            if self.use_buffer:
                if self.buffer_type == "CIRCLE":
                    args.append("-C")
                    args.append(str(self.buffer_size))
                else:
                    args.append("-S")
                    args.append(str(self.buffer_size))
            else:
                args.append("-p")
        if self.save_output:
            args.append("-o")
            if self.out_folder == "" or not os.path.isdir(self.out_folder):
                showDialog(window_title="Error: Invalid Output Folder",
                       dialog_text="Please enter a valid output folder",
                       icon_level=QMessageBox.Critical)
                return
            args.append(self.out_folder)
        if self.calc == "NONE":
            args.append("-n")
            args.append(self.img_folder)
            args.append(f"[{self.band_order}]")
        elif self.calc == "VOLUME":
            args.append("-v")
            args.append(self.img_folder)
        elif self.calc == "VOLUME_REF":
            args.append("-V")
            args.append(self.img_folder)
            if self.dem_path == "" or not os.path.isfile(self.dem_path):
                showDialog(window_title="Error: Invalid Reference DEM",
                       dialog_text="Please enter a valid reference DEM",
                       icon_level=QMessageBox.Critical)
                return
            args.append(self.dem_path)
        elif self.calc == "INDICES":
            if self.indices == "ALL":
                args.append("-a")
            else:
                args.append("-i")
                args.append(f"[{self.indices}]")
            args.append(self.img_folder)
            args.append(f"[{self.band_order}]")
        args.append(self.input_gpkg)
        args.append(self.output_gpkg)
        self.dlg.progress_bar.setValue(0)
        try:
            #pre_count = self.tm.countActiveTasks()
            ntask = QgsTask.fromFunction("zonal_stats_run",self.sub_wrapper,args)
            self.finished_signal.connect(self.completed)
            self.tm.addTask(ntask)
            task_count = self.tm.countActiveTasks()
            #print(task_count)
            #print("run")

        except Exception as e:
            showDialog(window_title="Error!",
                       dialog_text=e,
                       icon_level=QMessageBox.Critical)
            
    def completed(self,exception,result=None):
        #print("done")
        if result.returncode != 0:
            showDialog(window_title="Error!",
                       dialog_text=result.stderr.decode(),
                       icon_level=QMessageBox.Critical)
            with open(self.log,"w+") as f:
                f.write(result.stdout.decode())
                f.write(result.stderr.decode())
            return
        with open(self.log,"w+") as f:
            f.write(result.stdout.decode())
            f.write(result.stderr.decode())
        self.dlg.progress_bar.setValue(100)

    def sub_wrapper(self,task,args):
        if platform.system() == "Windows":
            res = subprocess.run(args, capture_output=True, shell=True)
        else:
            res = subprocess.run(args, capture_output=True)
        self.finished_signal.emit(res.returncode,res)
        return res
