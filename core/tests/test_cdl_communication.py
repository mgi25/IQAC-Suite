import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


@pytest.mark.django_db
def test_cdl_communication_create_and_list(client):
    # Per new policy: only admins can access the global log
    user = User.objects.create_superuser(
        username="alice", email="alice@example.com", password="pass123"
    )
    assert client.login(username="alice", password="pass123")

    url = reverse("api_cdl_communication")

    # Initially empty
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["messages"] == []

    # Create text only
    resp = client.post(url, {"comment": "Hello world"})
    assert resp.status_code == 201
    msg1 = resp.json()
    assert msg1["comment"] == "Hello world"

    # Create with attachment (small text file)
    uploaded = SimpleUploadedFile(
        "note.txt",
        b"Attachment content",
        content_type="text/plain",
    )
    resp = client.post(url, {"comment": "With file", "attachment": uploaded})
    assert resp.status_code == 201
    msg2 = resp.json()
    assert msg2.get("attachment_url")

    # List again should have 2 messages
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 2
    comments = {m["comment"] for m in data["messages"]}
    assert comments == {"Hello world", "With file"}


@pytest.mark.django_db
def test_cdl_communication_page_sets_csrf_cookie(client):
    # Use admin for access consistency with the API policy
    user = User.objects.create_superuser(
        username="bob", email="bob@example.com", password="pass123"
    )
    assert client.login(username="bob", password="pass123")

    resp = client.get(reverse("cdl_communication_page"))
    assert resp.status_code == 200
    assert "csrftoken" in resp.cookies
    assert bool(resp.cookies["csrftoken"].value)
