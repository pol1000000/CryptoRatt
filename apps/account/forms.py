from django.forms import ModelForm, CharField, PasswordInput, CheckboxInput, SelectMultiple, Select
from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import ugettext_lazy as _

from apps.account.models import UserProfile, ApiKey


class LDAPPassChangeForm(SetPasswordForm):
    old_password = CharField(label=_("Old password"), widget=PasswordInput)

    def clean_old_password(self):
        from django_auth_ldap.backend import LDAPBackend

        old_password = self.cleaned_data["old_password"]
        u = LDAPBackend().authenticate(self.user.username, old_password)
        if u is None:
            raise ValidationError(_("Incorrect password"))
        return old_password

    def save(self):
        old_password = self.cleaned_data["old_password"]
        new_password = self.cleaned_data["new_password1"]

        conn = self.user.ldap_user._get_connection()
        conn.simple_bind_s(self.user.ldap_user.dn, old_password.encode('utf-8'))
        conn.passwd_s(self.user.ldap_user.dn, old_password.encode('utf-8'), new_password.encode('utf-8'))

        return self.user

class UserProfileForm(ModelForm):
    class Meta:
        custom_themes = [
            ('bootstrap.default.min.css', 'Default'),
            ('bootstrap.cosmo.min.css', 'Cosmo'),
            ('bootstrap.cerulean.min.css', 'Cerulean'),
            ('bootstrap.darkly.min.css', 'Darkly'),
            ('bootstrap.flatly.min.css', 'Flatly'),
            ('bootstrap.litera.min.css', 'Litera'),
            ('bootstrap.pulse.min.css', 'Pulse'),
            ('bootstrap.lux.min.css', 'Lux'),
            ('bootstrap.lumen.min.css', 'Lumen'),
            ('bootstrap.litera.min.css', 'Litera'),
            ('bootstrap.slate.min.css', 'Slate'),
            ('bootstrap.spacelab.min.css', 'Spacelab'),
        ]

        model = UserProfile
        exclude = ('user', 'password_changed',)
        widgets = {
            'favourite_menu': CheckboxInput(attrs={'class': 'custom-control-input'}),
            'favourite_tags': SelectMultiple(attrs={'class': 'single-select'}),
            'theme': Select(
                choices=custom_themes,
                attrs={'class': 'form-control single-select'}),
            'items_per_page': Select(
                choices=[('10', 10), ('20', 20), ('30', 30), ('40', 40), ('50', 50)],
                attrs={'class': 'form-control single-select'}),
        }

class ApiKeyForm(ModelForm):
    class Meta:
        model = ApiKey
        exclude = ('user', 'key', 'active', 'created', 'expires')

    def save(self):
        if self.instance.expires < self.instance.created + timedelta(minutes=1):
            self.instance.expires = self.instance.created
        return super(ApiKeyForm, self).save()

LDAPPassChangeForm.base_fields.keyOrder = ['old_password', 'new_password1', 'new_password2']