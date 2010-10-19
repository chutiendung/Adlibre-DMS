import mimetypes
import os
import pickle

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _
from django.views.generic.simple import direct_to_template
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse

from converter import FileConverter


from fileshare.forms import UploadForm, SettingForm, EditSettingForm
from fileshare.models import (Rule, available_validators)
from fileshare.utils import ValidatorProvider, StorageProvider, SecurityProvider, DocCodeProvider


def index(request, template_name='fileshare/index.html', extra_context={}):
    """
    Upload file processing. Uploaded file will be check against available rules to
    determine storage, validator, and security plugins.
    """

    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            document = os.path.splitext(form.files['file'].name)[0]
            rule = Rule.objects.match(document)
            if rule:
                # check against all validator
                for validator in rule.get_validators():
                    if validator.is_storing_action and validator.active:
                        validator.perform(request, document)

                # check against all securities
                for security in rule.get_securities():
                    if security.is_storing_action and security.active:
                        security.perform(request, document)

                storage = rule.get_storage()
                storage.store(form.files['file'])
                messages.success(request, 'File has been uploaded.')
            else:
                messages.error(request, "No rule found for your uploaded file")
    extra_context['form'] = form
    return direct_to_template(request,
                              template_name,
                              extra_context=extra_context)


def get_file(request, hashcode, document, extension):
    rule = Rule.objects.match(document)
    if not rule:
        raise Http404

    hashplugin = rule.get_security('Hash')
    if hashplugin and not hashplugin.active:
        raise Http404
    if hashplugin.perform(request, document) != hashcode:
        return HttpResponse('Invalid hashcode')


    # check against all validator
    for validator in rule.get_validators():
        if validator.is_retrieval_action and validator.active:
            validator.perform(request, document)

    # check against all securities
    for security in rule.get_securities():
        if security.is_retrieval_action and security.active:
            security.perform(request, document)

    storage = rule.get_storage()
    filepath = storage.get(document)
    new_file = FileConverter(filepath, extension)
    mimetype, content = new_file.convert()

    response = HttpResponse(content, mimetype=mimetype)
    response["Content-Length"] = len(content)
    return response



def get_file_no_hash(request, document, extension):
    print document
    rule = Rule.objects.match(document)
    if not rule:
        print "x"
        raise Http404

    hashplugin = rule.get_security('Hash')
    if hashplugin and hashplugin.active:
        raise Http404


    # check against all validator
    for validator in rule.get_validators():
        if validator.is_retrieval_action and validator.active:
            validator.perform(request, document)

    # check against all securities
    for security in rule.get_securities():
        if security.is_retrieval_action and security.active:
            security.perform(request, document)


    storage = rule.get_storage()
    filepath = storage.get(document)
    new_file = FileConverter(filepath, extension)
    try:
        mimetype, content = new_file.convert()
    except TypeError:
        return HttpResponse("No file converter")
    response = HttpResponse(content, mimetype=mimetype)
    response["Content-Length"] = len(content)
    return response


@staff_member_required
def setting(request, template_name='fileshare/setting.html',
            extra_context={}):
    """
    Setting for adding and editing rule.
    """

    rule_list = Rule.objects.all()
    if request.method == 'POST':
        form = SettingForm(request.POST)
        if form.is_valid():
            rule = Rule()
            rule.doccode = pickle.dumps(DocCodeProvider.plugins[form.cleaned_data['doccode']]())
            rule.storage = pickle.dumps(StorageProvider.plugins[form.cleaned_data['storage']]())
            rule.securities = pickle.dumps([SecurityProvider.plugins[item]()
                for item in form.cleaned_data['securities']])
            rule.validators = pickle.dumps([ValidatorProvider.plugins[item]()
                for item in form.cleaned_data['validators']])
            rule.save()
            messages.success(request, 'New rule added.')
    else:
        form = SettingForm()

    extra_context['form'] = form
    extra_context['rule_list'] = rule_list
    return direct_to_template(request, template_name, extra_context=extra_context)


@staff_member_required
def edit_setting(request, rule_id, template_name='fileshare/edit_setting.html',
                   extra_context={}):
    rule = get_object_or_404(Rule, id=rule_id)
    initial = {
        'storage':rule.get_storage().name,
        'validators':[item.name for item in rule.get_validators()],
        'securities':[item.name for item in rule.get_securities()]
    }
    form = EditSettingForm(request.POST or initial)
    if request.method == 'POST':
        if form.is_valid():
            rule.storage = pickle.dumps(StorageProvider.plugins[form.cleaned_data['storage']]())
            rule.securities = pickle.dumps([SecurityProvider.plugins[item]()
                for item in form.cleaned_data['securities']])
            rule.validators = pickle.dumps([ValidatorProvider.plugins[item]()
                for item in form.cleaned_data['validators']])
            rule.save()
            messages.success(request, 'Rule details updated.')
            return HttpResponseRedirect(reverse('setting'))

    extra_context['rule'] = rule
    extra_context['form'] = form
    return direct_to_template(request, template_name, extra_context=extra_context)


@staff_member_required
def toggle_rule_state(request, rule_id):
    """
    Toggle rule state of being active or disabled
    """

    rule = get_object_or_404(Rule, id=rule_id)
    rule.active = not rule.active
    rule.save()
    return HttpResponseRedirect(reverse("setting"))


@staff_member_required
def toggle_securities_plugin(request, rule_id, plugin_index):
    rule = get_object_or_404(Rule, id=rule_id)
    plugins = rule.get_securities()
    plugin = plugins[int(plugin_index)]
    plugin.active = not plugin.active
    plugins[int(plugin_index)] = plugin
    rule.securities = pickle.dumps(plugins)
    rule.save()
    return HttpResponseRedirect(reverse("setting"))


@staff_member_required
def toggle_validators_plugin(request, rule_id, plugin_index):
    rule = get_object_or_404(Rule, id=rule_id)
    plugins = rule.get_validators()
    plugin = plugins[int(plugin_index)]
    plugin.active = not plugin.active
    plugins[int(plugin_index)] = plugin
    rule.validators = pickle.dumps(plugins)
    rule.save()
    return HttpResponseRedirect(reverse("setting"))


def plugin_setting(request, rule_id, plugin_type, plugin_index, template_name='fileshare/plugin_setting.html',
                   extra_context={}):
    """
    Some plugins have configuration and the configuration can be different for
    each rule.
    """

    rule = get_object_or_404(Rule, id=rule_id)
    if plugin_type == 'validator':
        plugins = rule.get_validators()
    else:
        plugins = rule.get_securities()
    plugin = plugins[int(plugin_index)]
    formclass = plugin.get_form()
    form = formclass(plugin, request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            plugins[int(plugin_index)] = plugin
            if plugin_type == 'validator':
                rule.validators = pickle.dumps(plugins)
            else:
                rule.securities = pickle.dumps(plugins)
            rule.save()
    extra_context['plugin'] = plugin
    extra_context['rule'] = rule
    extra_context['form'] = form
    print plugin.render()

    return direct_to_template(request, template_name, extra_context=extra_context)



def plugin_action(request, rule_id, plugin_type, plugin_index, action,
                   extra_context={}):
    """

    """

    rule = get_object_or_404(Rule, id=rule_id)
    if plugin_type == 'validator':
        plugins = rule.get_validators()
    else:
        plugins = rule.get_securities()
    plugin = plugins[int(plugin_index)]
    view = plugin.action(action)
    return view(request, rule, plugin, rule_id, plugin_type, plugin_index)

