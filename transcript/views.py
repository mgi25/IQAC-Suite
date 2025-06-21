from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def graduate_transcript(request):
    return render(request, 'transcript/graduate_transcript.html')
