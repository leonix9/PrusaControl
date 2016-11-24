import ast
import logging
from abc import ABCMeta, abstractmethod
from cStringIO import StringIO
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.cElementTree as ET

import io

import numpy


from stl.mesh import Mesh

from sceneData import ModelTypeStl

fileExtension = 'prus'


class ProjectFile(object):

    def __init__(self, scene, filename=""):
        if filename:
            self.scene_xml = None
            self.scene = scene

            #TODO:check which version is scene.xml version and according to chose class to read project file
            self.version = Version_1_0()
            self.version.load(scene, filename)
        else:
            self.version = Version_1_0()
            self.scene = scene

    def save(self, filename):
        self.version.save(self.scene, filename)


class VersionAbstract(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def check_version(self, filename):
        return False

    @abstractmethod
    def get_version(self):
        return "Abstract version"

    @abstractmethod
    def load(self, scene, filename):
        logging.debug("This is abstract version class load function")
        return False

    @abstractmethod
    def save(self, scene, filename):
        logging.debug("This is abstract version class save function")
        return False


class Version_1_0(VersionAbstract):

    def __init__(self):
        self.xmlFilename = 'scene.xml'

    def check_version(self, filename):
        return True

    def get_version(self):
        return "1.0"

    def load(self, scene, filename):
        #open zipfile
        with ZipFile(filename, 'r') as openedZipfile:
            tree = ET.fromstring(openedZipfile.read(self.xmlFilename))
            version = tree.find('version').text
            if self.get_version() == version:
                logging.debug("Ano, soubor je stejna verze jako knihovna pro jeho nacitani. Pokracujeme")
            else:
                logging.debug("Problem, tuto verzi neumim nacitat.")
                return False
            models = tree.find('models')
            models_data = []
            for model in models.findall('model'):
                model_data = {}
                model_data['file_name'] = model.get('name')
                model_data['normalization'] = ast.literal_eval(model.find('normalization').text)
                model_data['position'] = ast.literal_eval(model.find('position').text)
                model_data['rotation'] = ast.literal_eval(model.find('rotation').text)
                model_data['scale'] = ast.literal_eval(model.find('scale').text)
                models_data.append(model_data)

            scene.models = []
            for m in models_data:
                logging.debug("Jmeno souboru je: " + m['file_name'])
                mesh = Mesh.from_file(filename="", fh=openedZipfile.open(m['file_name']))
                model = ModelTypeStl.load_from_mesh(mesh, filename=m['file_name'], normalize=not m['normalization'])
                model.rotation_matrix = numpy.array(m['rotation'])
                model.pos = numpy.array(m['position'])
                model.scale_matrix = numpy.array(m['scale'])
                model.update_min_max()
                model.parent = scene

                scene.models.append(model)

    def save(self, scene, filename):
        #create zipfile
        with ZipFile(filename, 'w', ZIP_DEFLATED) as openedZipfile:
            #create xml file describing scene
            root = ET.Element("scene")
            ET.SubElement(root, "version").text=self.get_version()
            models_tag = ET.SubElement(root, "models")

            for model in scene.models:
                if model.isVisible:
                    model_element = ET.SubElement(models_tag, "model", name=model.filename)
                    ET.SubElement(model_element, "normalization").text=str(model.normalization_flag)
                    ET.SubElement(model_element, "position").text=str(model.pos.tolist())
                    ET.SubElement(model_element, "rotation").text=str(model.rotation_matrix.tolist())
                    ET.SubElement(model_element, "scale").text=str(model.scale_matrix.tolist())
                    #ET.SubElement(model_element, "rotation").text=str([.0, .0, .0])
                    #ET.SubElement(model_element, "scale").text=str([1., 1., 1.])


            #save xml file to new created zip file
            newXml = ET.tostring(root)
            openedZipfile.writestr(self.xmlFilename, newXml)

            #write stl files to zip file
            for model in scene.models:
                if model.isVisible:
                    #transform data to stl file
                    #mesh = self._create_mesh_from_model(model)
                    mesh = model.get_mesh(False, False)

                    #generate ascii format of stl(bug in numpy-stl)
                    #fileHandler = opened_zipfile.write(model.filename)
                    fileLike = StringIO()
                    mesh._write_ascii(fh=fileLike, name=model.filename)
                    openedZipfile.writestr(model.filename, fileLike.getvalue())
                    fileLike.close()

        return True


