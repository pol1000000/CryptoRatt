from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.base import File
from django.http import HttpResponse

from tastypie import fields, http
from tastypie.authentication import SessionAuthentication, MultiAuthentication
from tastypie.validation import FormValidation
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.exceptions import Unauthorized

from apps.account.authentication import MultiApiKeyAuthentication
from apps.cred.models import Cred, Tag, CredAudit
from apps.cred.forms import TagForm

class CredAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        # List views remove the deletes and historical credentials
        return object_list.filter(is_deleted=False, latest=None)

    def read_detail(self, object_list, bundle):
        # Check user has perms
        if not bundle.obj.is_visible_by(bundle.request.user):
            return False

        # This audit should go somewhere else, is there a detail list function we can override?
        CredAudit(audittype=CredAudit.CREDPASSVIEW, cred=bundle.obj, user=bundle.request.user).save()
        return True

    def create_list(self, object_list, bundle):
        # Assuming their auto-assigned to ``user``.
        raise Unauthorized("Not yet implemented.")

    def create_detail(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")

    def update_list(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")

    def update_detail(self, object_list, bundle):
        # Check user has perms
        if not bundle.obj.is_owned_by(bundle.request.user):
            return False

        CredAudit(audittype=CredAudit.CREDCHANGE, cred=bundle.obj, user=bundle.request.user).save()
        return True

    def delete_list(self, object_list, bundle):
        # Sorry user, no deletes for you!
        raise Unauthorized("Not yet implemented.")

    def delete_detail(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")


class TagAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list

    def read_detail(self, object_list, bundle):
        return True

    def create_list(self, object_list, bundle):
        # Assuming their auto-assigned to ``user``.
        raise Unauthorized("Not yet implemented.")

    def create_detail(self, object_list, bundle):
        return True

    def update_list(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")

    def update_detail(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")

    def delete_list(self, object_list, bundle):
        # Sorry user, no deletes for you!
        raise Unauthorized("Not yet implemented.")

    def delete_detail(self, object_list, bundle):
        raise Unauthorized("Not yet implemented.")


class CredResource(ModelResource):
    def get_object_list(self, request):
        # Only show latest, not deleted and accessible credentials
        return Cred.objects.visible(request.user, historical=True, deleted=True)

    def dehydrate(self, bundle):
        # Workaround for this tastypie issue:
        # https://github.com/toastdriven/django-tastypie/issues/201
        bundle.data['username'] = bundle.obj.username

        # Add a value indicating if something is on the change queue
        bundle.data['on_changeq'] = bundle.obj.on_changeq()

        # Unless you are viewing the details for a cred, hide the password
        if self.get_resource_uri(bundle) != bundle.request.path:
            del bundle.data['password']

        return bundle

    def post_detail(self, request, **kwargs):
        basic_bundle = self.build_bundle(request=request)

        try:
            obj = self.cached_obj_get(bundle=basic_bundle, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return http.HttpNotFound()
        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one resource is found at this URI.")

        obj.save()

        if not self._meta.always_return_data:
            return http.HttpAccepted()
        else:
            bundle = self.build_bundle(obj=obj, request=request)
            bundle = self.full_dehydrate(bundle)
            bundle = self.alter_detail_data_to_serialize(request, bundle)
            return self.create_response(request, bundle, response_class=http.HttpAccepted)

    class Meta:
        queryset = Cred.objects.filter(is_deleted=False, latest=None)
        always_return_data = True
        resource_name = 'cred'
        excludes = ['username', 'is_deleted']
        authentication = MultiAuthentication(SessionAuthentication(), MultiApiKeyAuthentication())
        authorization = CredAuthorization()
        filtering = {
            'title': ('exact', 'contains', 'icontains'),
            'url': ('exact', 'startswith', ),
        }


class TagResource(ModelResource):
    # When showing a tag, show all the creds under it, that we are allowed to see
    creds = fields.ToManyField(CredResource,
        attribute=lambda bundle: Cred.objects.visible(bundle.request.user).filter(tags=bundle.obj),
        null=True,
    )

    class Meta:
        queryset = Tag.objects.all()
        always_return_data = True
        filtering = {
            'name': ('exact', 'contains', 'icontains', 'startswith', 'istartswith'),
        }
        resource_name = 'tag'
        authentication = MultiAuthentication(SessionAuthentication(), MultiApiKeyAuthentication())
        authorization = TagAuthorization()
        validation = FormValidation(form_class=TagForm)
