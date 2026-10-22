import json

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from .draw import make_pairs
from .models import Participant


def post(client, url, data=None):
    return client.post(url, json.dumps(data or {}), content_type="application/json")


class MakePairsTests(SimpleTestCase):
    def test_valid_for_many_group_sizes(self):
        # run it many times because the shuffle is random
        for size in range(3, 10):
            for _ in range(100):
                pairs = make_pairs(range(size))
                giftee_of = dict(pairs)

                self.assertEqual(len(giftee_of), size)
                self.assertEqual(sorted(giftee_of.values()), list(range(size)))
                for giver, giftee in pairs:
                    self.assertNotEqual(giver, giftee)
                    self.assertNotEqual(giftee_of[giftee], giver)


class SecretSantaApiTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("boss", password="secret123")
        self.admin = self.client_class()
        self.admin.login(username="boss", password="secret123")

    def make_users(self, count):
        self.clients = {}
        self.ids = {}
        for i in range(count):
            name = f"user{i}"
            client = self.client_class()
            response = post(client, "/auth/signup", {
                "username": name,
                "password": "secret123",
                "name": f"User {i}",
            })
            self.clients[name] = client
            self.ids[name] = response.json()["id"]

    def test_signup_needs_a_long_enough_password(self):
        response = post(self.client, "/auth/signup", {"username": "a", "password": "short"})
        self.assertEqual(response.status_code, 400)

    def test_draw_gives_everyone_a_giftee(self):
        self.make_users(6)
        self.assertEqual(self.admin.post("/draw/run").status_code, 200)

        for person in Participant.objects.all():
            self.assertIsNotNone(person.giftee)
            self.assertNotEqual(person.giftee, person)
            self.assertNotEqual(person.giftee.giftee, person)

    def test_draw_needs_enough_people(self):
        self.make_users(2)
        self.assertEqual(self.admin.post("/draw/run").status_code, 400)

    def test_draw_can_only_run_once(self):
        self.make_users(3)
        self.admin.post("/draw/run")
        self.assertEqual(self.admin.post("/draw/run").status_code, 409)

    def test_draw_is_admin_only(self):
        self.make_users(3)
        self.assertEqual(self.clients["user0"].post("/draw/run").status_code, 403)

    def test_my_giftee_only_shows_own_assignment(self):
        self.make_users(4)
        self.admin.post("/draw/run")

        response = self.clients["user0"].get("/my-giftee")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(list(body.keys()), ["giftee"])
        self.assertEqual(sorted(body["giftee"].keys()), ["name", "wishlist"])

        me = Participant.objects.get(user__username="user0")
        self.assertEqual(body["giftee"]["name"], me.giftee.display_name())

    def test_my_giftee_before_the_draw(self):
        self.make_users(3)
        self.assertEqual(self.clients["user0"].get("/my-giftee").status_code, 404)

    def test_gifter_sees_the_wishlist(self):
        self.make_users(3)
        target = self.ids["user0"]
        self.clients["user0"].patch(
            f"/participant/{target}/wishlist",
            json.dumps({"wishlist": "a good book"}),
            content_type="application/json",
        )
        self.admin.post("/draw/run")

        gifter = Participant.objects.get(giftee_id=target)
        response = self.clients[gifter.user.username].get("/my-giftee")
        self.assertEqual(response.json()["giftee"]["wishlist"], "a good book")

    def test_wishlist_giver_view_does_not_reveal_the_giver(self):
        self.make_users(3)
        self.admin.post("/draw/run")

        response = self.clients["user0"].get("/my-wishlist-giver")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(sorted(body.keys()), ["draw_done", "has_gifter", "my_wishlist"])
        self.assertTrue(body["has_gifter"])

    def test_signup_is_closed_after_the_draw(self):
        self.make_users(3)
        self.admin.post("/draw/run")
        late = post(self.client_class(), "/auth/signup", {"username": "late", "password": "secret123"})
        self.assertEqual(late.status_code, 403)

    def test_manual_lock_closes_signup_but_draw_still_runs(self):
        self.make_users(3)
        self.assertEqual(self.admin.post("/draw/lock").status_code, 200)
        late = post(self.client_class(), "/auth/signup", {"username": "late", "password": "secret123"})
        self.assertEqual(late.status_code, 403)
        self.assertEqual(self.admin.post("/draw/run").status_code, 200)

    def test_cannot_read_or_edit_someone_elses_profile(self):
        self.make_users(3)
        other = self.ids["user1"]
        me = self.clients["user0"]
        self.assertEqual(me.get(f"/participant/{other}").status_code, 403)
        response = me.patch(
            f"/participant/{other}/wishlist",
            json.dumps({"wishlist": "hacked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_own_profile(self):
        self.make_users(3)
        mine = self.ids["user0"]
        self.assertEqual(self.clients["user0"].get(f"/participant/{mine}").status_code, 200)

    def test_participants_list_has_names_only(self):
        self.make_users(3)
        self.admin.post("/draw/run")
        body = self.clients["user0"].get("/participants").json()
        for entry in body["participants"]:
            self.assertEqual(sorted(entry.keys()), ["id", "name"])

    def test_admin_can_remove_before_the_draw_only(self):
        self.make_users(4)
        first = self.ids["user0"]
        second = self.ids["user1"]

        self.assertEqual(self.clients["user2"].delete(f"/participant/{first}").status_code, 403)
        self.assertEqual(self.admin.delete(f"/participant/{first}").status_code, 200)
        self.assertFalse(Participant.objects.filter(pk=first).exists())

        self.admin.post("/draw/run")
        self.assertEqual(self.admin.delete(f"/participant/{second}").status_code, 409)

    def test_login_is_needed(self):
        self.assertEqual(self.client.get("/participants").status_code, 401)
        self.assertEqual(self.client.get("/my-giftee").status_code, 401)
