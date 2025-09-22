import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from emt.models import EventProposal, CDLAssignment, CDLTaskAssignment


@pytest.mark.django_db
def test_cdl_thread_access_rules(client):
    # Users
    superuser = User.objects.create_superuser('root', 'root@example.com', 'pass')
    owner = User.objects.create_user('owner', password='pass')
    employee = User.objects.create_user('emp', password='pass')
    stranger = User.objects.create_user('str', password='pass')

    # Proposal
    prop = EventProposal.objects.create(submitted_by=owner, event_title='E1')

    url = reverse('cdl_thread', kwargs={'proposal_id': prop.id})

    # Owner allowed
    assert client.login(username='owner', password='pass')
    assert client.get(url).status_code == 200
    client.logout()

    # Superuser allowed
    assert client.login(username='root', password='pass')
    assert client.get(url).status_code == 200
    client.logout()

    # Stranger blocked
    assert client.login(username='str', password='pass')
    assert client.get(url).status_code == 403
    client.logout()

    # Employee assigned via CDLAssignment allowed
    CDLAssignment.objects.create(proposal=prop, assignee=employee)
    assert client.login(username='emp', password='pass')
    assert client.get(url).status_code == 200
    client.logout()

    # New proposal, assign per-resource task
    prop2 = EventProposal.objects.create(submitted_by=owner, event_title='E2')
    CDLTaskAssignment.objects.create(proposal=prop2, resource_key='poster', assignee=employee)
    url2 = reverse('cdl_thread', kwargs={'proposal_id': prop2.id})
    assert client.login(username='emp', password='pass')
    assert client.get(url2).status_code == 200
    client.logout()
