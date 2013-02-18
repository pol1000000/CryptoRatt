from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User, Group
from models import NewUserForm

@staff_member_required
def home(request):
    userlist = User.objects.all() 
    grouplist = Group.objects.all()
    return render(request, 'staff_home.html', {'userlist': userlist, 'grouplist': grouplist})

@staff_member_required
def userdetail(request, uid):
    user = get_object_or_404(User, pk=uid)
    return render(request, 'staff_userdetail.html', {'user' : user})

class NewUser(FormView):
    form_class = NewUserForm
    template_name = 'staff_useredit.html'
    success_url = '/staff/'

    # Staff access only
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super(NewUser, self).dispatch(*args, **kwargs)

    # Create the user, set password to newpass
    def form_valid(self, form):
        user = form.save()
        user.set_password(form.cleaned_data['newpass'])
        user.save()
        return super(NewUser, self).form_valid(form)


