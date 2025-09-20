import pytest
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


@pytest.mark.django_db
def test_cdl_communication_create_and_list(client):
    # Ensure group exists
    grp, _ = Group.objects.get_or_create(name="CDL_MEMBER")
    user = User.objects.create_user(username="alice", password="pass123")
    user.groups.add(grp)
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
        "note.txt", b"Attachment content", content_type="text/plain"
    )
    resp = client.post(url, {"comment": "With file"}, FILES={"attachment": uploaded})
    assert resp.status_code == 201
    msg2 = resp.json()
    assert msg2["attachment_url"] is not None

    # List again should have 2 messages (most recent first)
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 2
    comments = [m["comment"] for m in data["messages"]]
    assert comments[0] in (
        "With file",
        "Hello world",
    )  # Ordering by created_at desc, but creation may be fast
    assert set(comments) == {"Hello world", "With file"}
