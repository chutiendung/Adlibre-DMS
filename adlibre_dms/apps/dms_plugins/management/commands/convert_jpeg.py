"""
Module: Jpeg to PNG thumbnail converter for Adlibre DMS

Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2013
License: See LICENSE for license information
Author: Iurii Garmash (yuri@adlibre.com.au)
"""

from optparse import make_option
from PIL import Image

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Converts from JPEG image into PNG thumbnail"""
    args = 'thumbnail_path'

    def __init__(self):
        BaseCommand.__init__(self)
        self.option_list += (
            make_option(
                '--quiet', '-q',
                default=False,
                action='store_true',
                help='Hide all command output'),
        )

    def handle(self, *args, **options):
        size = 65, 65
        quiet = options.get('quiet', False)
        if len(args) == 0:
            if not quiet:
                self.stdout.write('No arguments specified\n')
            return

        if len(args) > 1:
            if not quiet:
                self.stdout.write('Please specify one path at a time\n')
            return
        if not quiet:
            self.stdout.write('Converting thumbnail\n')

        thumbnail_path = args[0]
        with Image.open(thumbnail_path) as im:
            self.stdout.write('%s %s\n' % im.size)
            self.stderr.write('resizing\n')
            img = im.thumbnail(size)
            img.save(thumbnail_path + '.png', 'PNG')

        img.save(thumbnail_path + '.png', 'PNG')
        if not quiet:
            self.stdout.write('Done!\n')