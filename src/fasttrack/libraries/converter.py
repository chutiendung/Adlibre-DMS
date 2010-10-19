import os
from subprocess import Popen, PIPE
import mimetypes

class FileConverter:

    def __init__(self, filepath, extension):
        self.filepath = filepath
        self.extension_to = extension


    def convert(self):
        filename = os.path.basename(self.filepath)
        document, extension = os.path.splitext(filename)
        extension_from = extension.strip(".")
        if self.extension_to == extension_from:
            content = open(self.filepath, 'rb').read()
            return [mimetypes.guess_type(self.filepath)[0], content]
        try:
            func = getattr(self, '%s_to_%s' % (extension_from, self.extension_to))
            return func()
        except AttributeError:
            return None


    def tif_to_pdf(self):
        filename = os.path.basename(self.filepath)
        document = os.path.splitext(filename)[0]
        path = '%s/%s.pdf' % (os.path.dirname(self.filepath), document)
        p = Popen('tiff2pdf %s -o %s' % (self.filepath, path), shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        content = open(path, 'rb').read()
        p = Popen('rm -rf %s' % path, shell=True,stdout=PIPE, stderr=PIPE)
        return ['application/pdf', content]

