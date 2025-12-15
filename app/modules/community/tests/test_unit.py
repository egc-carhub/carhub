from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community


def login(client, email="test@example.com", password="test1234"):
    return client.post("/login", data=dict(email=email, password=password), follow_redirects=True)


def test_join_and_leave_updates_database(test_client):
    # create community
    with test_client.application.app_context():
        comm = Community(name="CU_TestCommunity", description="desc")
        db.session.add(comm)
        db.session.commit()
        comm_id = comm.id

    # login as default test user
    rv = login(test_client)
    assert rv.status_code == 200

    # join via AJAX-like request (Accept: application/json)
    join_resp = test_client.post(f"/community/join/{comm_id}", headers={"Accept": "application/json"})
    assert join_resp.status_code == 200
    jdata = join_resp.get_json()
    assert jdata is not None and jdata.get("member") is True

    with test_client.application.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        comm_db = Community.query.get(comm_id)
        assert user in comm_db.community_members

    # leave
    leave_resp = test_client.post(f"/community/leave/{comm_id}", headers={"Accept": "application/json"})
    assert leave_resp.status_code == 200
    ldata = leave_resp.get_json()
    assert ldata is not None and ldata.get("member") is False

    with test_client.application.app_context():
        comm_db = Community.query.get(comm_id)
        assert user not in comm_db.community_members


def test_follow_community_and_receive_notification_on_publish(test_client):
    # create community and an author that will 'publish'
    with test_client.application.app_context():
        comm = Community(name="CU_NotifyCommunity", description="desc2")
        db.session.add(comm)
        db.session.commit()
        comm_id = comm.id
        # create an author user
    author = User(email="author_cu@example.com", password="secret")
    db.session.add(author)
    db.session.commit()
    author_id = author.id

    # login as test user
    rv = login(test_client)
    assert rv.status_code == 200

    # follow community
    r1 = test_client.post(f"/follow/community/{comm_id}", headers={"Accept": "application/json"})
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1.get("following") is True

    # Simulate a 'publish to community' event: create a notification for all community followers
    with test_client.application.app_context():
        from app.modules.notifications.models import Notification, user_follows_community

        # find followers of the community
        followers = (
            db.session.query(User)
            .join(user_follows_community, User.id == user_follows_community.c.user_id)
            .filter(user_follows_community.c.community_id == comm_id)
            .all()
        )
        # create notifications for followers
        for follower in followers:
            n = Notification(
                recipient_id=follower.id,
                actor_id=author_id,
                community_id=comm_id,
                type="community_dataset_added",
                message="New dataset in community",
            )
            db.session.add(n)
        db.session.commit()

    # login as test user and fetch notifications
    rv = login(test_client)
    assert rv.status_code == 200
    list_resp = test_client.get("/notifications")
    assert list_resp.status_code == 200
    data = list_resp.get_json()
    msgs = [n.get("message") for n in data]
    assert "New dataset in community" in msgs

    # Now unfollow and ensure no notification on subsequent publish
    r2 = test_client.post(f"/follow/community/{comm_id}", headers={"Accept": "application/json"})
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2.get("following") is False

    # create another notification as if a new dataset was added
    with test_client.application.app_context():
        from app.modules.notifications.models import Notification

        n2 = Notification(
            recipient_id=author_id,
            actor_id=author_id,
            community_id=comm_id,
            type="community_dataset_added",
            message="Another dataset",
        )
        db.session.add(n2)
        db.session.commit()

    # test user should NOT receive the new notification
    rv = login(test_client)
    list_resp2 = test_client.get("/notifications")
    data2 = list_resp2.get_json()
    msgs2 = [n.get("message") for n in data2]
    assert "Another dataset" not in msgs2
