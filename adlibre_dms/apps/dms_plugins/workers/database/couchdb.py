"""
Module: DMS CouchDB Plugin
Project: Adlibre DMS
Copyright: Adlibre Pty Ltd 2012
License: See LICENSE for license information
Author: Iurii Garmash
"""

from dms_plugins.pluginpoints import BeforeRetrievalPluginPoint, BeforeRemovalPluginPoint, DatabaseStoragePluginPoint
from dms_plugins.models import Document as DocTags #TODO: needs refactoring of name
from dms_plugins.workers import Plugin, PluginError, BreakPluginChain
from document_manager import DocumentManager
from dmscouch.models import CouchDocument
import os

class CouchDBMetadata(object):
    """
        Stores metadata in CouchDB DatabaseManager.
        Handles required logic for metadata <==> Document(object) manipulations.
    """

    def store(self, request, document):
        docrule = document.get_docrule()
        # doing nothing for no doccode documents
        if docrule.no_doccode:
            return document
        else:
            manager = DocumentManager()
            mapping = manager.get_plugin_mapping(document)
            # doing nothing for documents without mapping has DB plugins
            if not mapping.get_database_storage_plugins():
                return document
            else:
                # if not exists all required metadata getting them from doccode retrieve sequence
                if not document.metadata:
                    # HACK: Preserving db_info here... (May be Solution!!!)
                    db_info = document.get_db_info()
                    document = manager.retrieve(request, document.file_name, only_metadata=True)
                    document.set_db_info(db_info)
                # updating tags to sync with Django DB
                self.sync_document_tags(document)
                # assuming no document with this _id exists. SAVING
                couchdoc=CouchDocument()
                couchdoc.populate_from_dms(request, document)
                couchdoc.save(force_update=True)
                #print "Storing Document into DB", document
                return document

    def update_metadata_after_removal(self, request, document):
        """
        Updates document CouchDB metadata on removal. (Removes CouchDB document)
        """
        if not document.get_file_obj():
            #doc is fully deleted from fs
            stripped_filename=document.get_stripped_filename()
            couchdoc = CouchDocument.get(docid=stripped_filename)
            couchdoc.delete()
        return document
        #print "Deleted Document in DB", document

    def retrieve(self, request, document):

        manager = DocumentManager()
        mapping = manager.get_plugin_mapping(document)
        # doing nothing for no doccode documents
        # doing nothing for documents without mapping has DB plugins
        if document.get_docrule().no_doccode:
            return document
        else:
            if not mapping.get_database_storage_plugins():
                return document
            else:
                doc_name = document.get_stripped_filename()
                couchdoc = CouchDocument.get(docid=doc_name)
                document = couchdoc.populate_into_dms(request, document)
                #print "Populating Document from DB", document
                return document

    """
    Helper managers:
    """
    def sync_document_tags(self, document):
        if not document.tags:
            tags = []
            try:
                doc_model = DocTags.objects.get(name = document.get_stripped_filename())
                tags = doc_model.get_tag_list()
            except DocTags.DoesNotExist:
                pass
            document.set_tags(tags)
        return document.tags

class CouchDBMetadataRetrievalPlugin(Plugin, BeforeRetrievalPluginPoint):
    title = "CouchDB Metadata Retrieval"
    description = "Loads document metadata from CouchDB"

    plugin_type = 'database'
    worker = CouchDBMetadata()

    def work(self, request, document, **kwargs):
        return self.worker.retrieve(request, document)

class CouchDBMetadataStoragePlugin(Plugin, DatabaseStoragePluginPoint):
    title = "CouchDB Metadata Storage"
    description = "Saves document metadata CouchDB"

    plugin_type = 'database'
    worker = CouchDBMetadata()

    def work(self, request, document, **kwargs):
        return self.worker.store(request, document)

class CouchDBMetadataRemovalPlugin(Plugin, BeforeRemovalPluginPoint):
    title = "CouchDB Metadata Removal"
    description = "Updates document metadata after removal of document (or some revisions of document)"

    plugin_type = 'database'
    worker = CouchDBMetadata()

    def work(self, request, document, **kwargs):
        return self.worker.update_metadata_after_removal(request, document)