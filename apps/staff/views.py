from base64 import b64encode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.views.generic.edit import UpdateView, FormView
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext as _
from django_otp import user_has_device, devices_for_user
from django.core.files.uploadedfile import SimpleUploadedFile

import datetime
import json
from django.utils.timezone import now
from django.utils.timezone import utc

from apps.cred.models import CredAudit, Cred, Tag
from apps.cred.forms import CredForm
from apps.staff.forms import UserForm, GroupForm, AuditFilterForm
from apps.staff.forms import EditUserForm
from apps.staff.decorators import staff_required


@staff_required
def app_settings(request):
    return render(request, 'staff_tab_settings.html')

@staff_required
def users(request):
    paginator = Paginator(
        User.objects.all().order_by('username'),
        request.user.profile.items_per_page
    )
    
    page = request.GET.get('page')
    users = paginator.get_page(page)    
    
    return render(request, 'staff_tab_users.html', {'users': users})

@staff_required
def groups(request):
    paginator = Paginator(
        Group.objects.all().order_by('name'),
        request.user.profile.items_per_page
    )
    
    page = request.GET.get('page')
    groups = paginator.get_page(page)    

    return render(request, 'staff_tab_groups.html', {'groups': groups})

@staff_required
def tags(request):
    paginator = Paginator(
        Tag.objects.all().order_by('name'),
        request.user.profile.items_per_page
    )
    
    page = request.GET.get('page')
    tags = paginator.get_page(page)    

    return render(request, 'staff_tab_tags.html',  {'tags': tags})

@staff_required
def trash(request):
    paginator = Paginator(
        Cred.objects.filter(is_deleted=True).order_by('title'),
        request.user.profile.items_per_page
    )
    
    page = request.GET.get('page')
    creds = paginator.get_page(page)    

    return render(request, 'staff_tab_trash.html',  {'creds': creds})


@staff_required
def user_detail(request, uid):
    user = get_object_or_404(User, pk=uid)
    credlogs = CredAudit.objects.filter(user=user, cred__group__in=request.user.groups.all())[:5]
    
    # disable user if it don`t exists in LDAP
    if settings.LDAP_ENABLED and settings.USE_LDAP_GROUPS:
        from django_auth_ldap.backend import LDAPBackend
        popuser = LDAPBackend().populate_user(user.username)
        if popuser is None:
            user.is_active = False
            user.save()

    return render(
        request, 'staff_detail_user.html',
        {'viewuser': user, 'credlogs': credlogs,})

@staff_required
def group_detail(request, gid):
    group = get_object_or_404(Group, pk=gid)
    return render(request, 'staff_detail_group.html', {'group': group})

@staff_required
def tag_detail(request, tid):
    tag = get_object_or_404(Tag, pk=tid)
    return render(request, 'staff_detail_tag.html', {'tag': tag})

@staff_required
def group_add(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            request.user.groups.add(form.instance)
            return HttpResponseRedirect(reverse('staff:settings'))
    else:
        form = GroupForm()

    return render(request, 'staff_groupedit.html', {'form': form})

@staff_required
def edit_group(request, gid):
    group = get_object_or_404(Group, pk=gid)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('staff:groups'))
    else:
        form = GroupForm(instance=group)

    return render(request, 'staff_edit_group.html', {'edit_group': group, 'form': form})


@staff_required
def delete_group(request, gid):
    group = get_object_or_404(Group, pk=gid)
    if request.method == 'POST':
        group.delete()
    return HttpResponseRedirect(reverse('staff:groups'))


@staff_required
def delete_user(request, uid):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=uid)
        user.delete()
    return HttpResponseRedirect(reverse('staff:users'))

@staff_required
def delete_tag(request, tid):
    tag = get_object_or_404(Tag, pk=tid)
    if request.method == 'POST':
        tag.delete()
    return HttpResponseRedirect(reverse('staff:tags'))


@staff_required
def audit(request, by, byarg):
    auditlog = CredAudit.objects.all()
    audit_item = None

    if by == 'user':
        audit_item = get_object_or_404(User, pk=byarg)
        auditlog = auditlog.filter(user=audit_item)
    elif by == 'cred':
        audit_item = get_object_or_404(Cred, pk=byarg)
        auditlog = auditlog.filter(cred=audit_item)
    elif by == 'days':
        audit_item = int(byarg)
        try:
            delta = datetime.timedelta(days=int(byarg))
            datefrom = now() - delta
        except OverflowError:
            datefrom = datetime.datetime(1970, 1, 1).replace(tzinfo=utc)
        auditlog = auditlog.filter(time__gte=datefrom)

    if request.method == 'POST':
        form = AuditFilterForm(request.POST)
    else:
        form = AuditFilterForm()

    if form.is_valid():
        auditlog = auditlog.exclude(audittype__in=form.cleaned_data['hide'])

    paginator = Paginator(auditlog, request.user.profile.items_per_page)
    page = request.GET.get('page')

    try:
        audit_logs = paginator.page(page)
    except PageNotAnInteger:
        audit_logs = paginator.page(1)
    except EmptyPage:
        audit_logs = paginator.page(paginator.num_pages)

    return render(request, 'staff_audit.html', {
        'audit_item': audit_item,
        'filterform': form,
        'audit_logs': audit_logs,
        'by': by,
        'byarg': byarg
    })

class NewUser(FormView):
    form_class = UserForm
    template_name = 'staff_edit_user.html'
    success_url = reverse_lazy('staff:settings')

    # Staff access only
    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(NewUser, self).dispatch(*args, **kwargs)

    # Create the user, set password to newpass
    def form_valid(self, form):
        user = form.save()
        user.set_password(form.cleaned_data['newpass'])
        user.save()
        return super(NewUser, self).form_valid(form)

@staff_required
def edit_user(request, uid):
    edituser = get_object_or_404(User, pk=uid)
    
    if request.method == 'POST':
        form = EditUserForm(request.POST, request.FILES, request.user, instance=edituser)

        if form.is_valid():
            saved_form = form.save()

            if request.FILES.getlist('icon'):
                edituser_profile = edituser.profile
                f = request.FILES.getlist('icon')[0]
                edituser_profile.avatar = b64encode(f.file.read())
                edituser_profile.save()

            return HttpResponseRedirect(reverse('staff:user_detail', args=(uid,)))
    else:
        form = EditUserForm(instance=edituser)

    return render(request, 'staff_edit_user.html', {'edit_user':  edituser, 'form': form})


# TODO: Move to API
@staff_required 
def deactivate_user(request):
    if request.method == 'POST':
        request_json = json.loads(request.body)

        user = get_object_or_404(User, pk=request_json['user_id'])
        user.is_active = request_json['is_active']
        user.save()

        return JsonResponse({'user_id':request_json['user_id'], 'is_active': user.is_active})
    return Http404


@staff_required
def credundelete(request, cred_id):
    cred = get_object_or_404(Cred, pk=cred_id)

    try:
        lastchange = CredAudit.objects.filter(
            cred=cred,
            audittype__in=[CredAudit.CREDCHANGE, CredAudit.CREDADD],
        ).latest().time
    except CredAudit.DoesNotExist:
        lastchange = _("Unknown (Logs deleted)")

    # Check user has perms
    if not cred.is_owned_by(request.user):
        raise Http404
    if request.method == 'POST':
        CredAudit(audittype=CredAudit.CREDADD, cred=cred, user=request.user).save()
        cred.is_deleted = False
        cred.save()
        return HttpResponseRedirect(reverse('cred:cred_list', args=('special', 'trash')))

    CredAudit(audittype=CredAudit.CREDVIEW, cred=cred, user=request.user).save()

    return render(request, 'cred_detail.html', {'cred': cred, 'lastchange': lastchange, 'action': reverse('cred:cred_delete', args=(cred_id,)), 'undelete': True})


@staff_required
def delete_token(request, uid):
    # Grab the user
    user = get_object_or_404(User, pk=uid)

    # Show confirm form on GET
    if request.method != 'POST':
        return render(request, 'staff_removetoken.html', {
            'user': user,
        })

    # Delete all devices (backup, token and phone)
    for dev in devices_for_user(user):
        dev.delete()

    # Redirect to the users detail page
    return HttpResponseRedirect(reverse('staff:user_detail', args=(uid,)))
