# core/views.py

from django.shortcuts               import render, redirect
from django.contrib.auth            import logout
from django.contrib.auth.decorators import login_required

# import your model
from .models import EventProposal
from django.shortcuts import render

def login_view(request):
    # Simply show the login page; the form action in the template will point
    # to allauth’s Google login URL via the provider_login_url tag.
    return render(request, 'core/login.html')



def logout_view(request):
    """
    Log out locally and send back to the login page.
    """
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')


@login_required
def propose_event(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        desc  = request.POST.get('description')
        EventProposal.objects.create(
            user=request.user,
            title=title,
            description=desc
        )
        return redirect('dashboard')
    return render(request, 'core/event_proposal.html')
