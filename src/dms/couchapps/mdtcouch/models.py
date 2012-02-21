"""
Module: DMS CocuhDB Metadata Templates Model
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2011
License: See LICENSE for license information
Author: Iurii Garmash
"""

#from datetime import datetime
from couchdbkit.ext.django.schema import *

class MetaDataTemplate(Document):
    """
    Base Metadata Template manager.
    Uses CouchDB for operating.
    """
    docrule_id = StringProperty(default = "")
    description = StringProperty(default = "")
    fields = DictProperty(default = {})
    parallel_keys = DictProperty(default = {})

    class Meta:
        app_label = "mdtcouch"

    def populate_from_DMS(self, mdt_data):
        self.docrule_id = mdt_data["docrule_id"]
        self.description = mdt_data["description"]
        self.fields = mdt_data["fields"]
        self.parallel_keys = mdt_data["parallel"]
        return self