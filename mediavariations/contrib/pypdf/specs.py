import cStringIO

from django.core.files import File
from django.core.files.base import ContentFile

from pyPdf import PdfFileWriter, PdfFileReader

from ...specs import Base


class PageRange(Base):
    defaults = {
        'start' : 0,
        'stop' : 1
    }

    def process(self):
        options = self.get_options()
        reader = PdfFileReader(self.original)
        output = PdfFileWriter()

        for n in range(options['start'], options['stop']):
            try:
                output.addPage(reader.pages[n])
            except IndexError:
                pass

        memfile = cStringIO.StringIO()
        output.write(memfile)
        content_file = ContentFile(memfile.getvalue())
        memfile.close()

        return self.storage.save(self.variation_path, content_file)




