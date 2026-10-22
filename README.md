# Secret Santa Backend

A small REST API for running a Secret Santa draw. People sign up, an admin runs the draw, and each person can only see who they are giving a gift to.

Built with Python, Django and SQLite.

## Features

- Signup, login and logout using Django's session authentication
- The draw gives every participant a giftee, never themselves
- No mutual pairs (A gives to B and B gives to A) when there are 3 or more people
- `/my-giftee` returns only the caller's own assignment
- Signups are locked once the draw runs, and an admin can also lock manually
- Each participant has a wishlist that their gifter can see
- Admin removal of participants before the draw

## Setup

You need Python 3.10 or newer.

```
git clone <your-repo-url>
cd secret-santa-backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The superuser is the admin. It is not a participant, so it is not part of the draw. The server runs at http://127.0.0.1:8000.

To run the tests:

```
python manage.py test
```

## Endpoints

All request and response bodies are JSON. The `{id}` in a url is the user id returned by signup and login.

| Method | Path | Who | What it does |
|--------|------|-----|--------------|
| POST | /auth/signup | anyone | Create an account (`username`, `password` of 8+ characters, optional `name`, `email`, `wishlist`). Closed once the draw is locked. |
| POST | /auth/login | anyone | Log in with `username` and `password`. |
| POST | /auth/logout | logged in | Log out. |
| GET | /participants | logged in | List of names and ids. No assignments. |
| GET | /participant/{id} | owner only | Your own profile. Other ids return 403. |
| PATCH | /participant/{id}/wishlist | owner only | Update your wishlist (`wishlist`, max 500 characters). |
| DELETE | /participant/{id} | admin | Remove a participant. Only before the draw. |
| GET | /draw/status | anyone | Participant count, minimum needed, locked and drawn flags. |
| POST | /draw/run | admin | Run the draw. Needs at least 3 participants. Locks signups. |
| POST | /draw/lock | admin | Close signups without running the draw. The draw can still be run afterwards. |
| GET | /my-giftee | logged in | Name and wishlist of the person you give to. |
| GET | /my-wishlist-giver | logged in | Whether someone is assigned to you, and your own wishlist. Does not say who. |

## Trying it with curl

```
# sign up, saving the session cookie
curl -c cookies.txt -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username": "asha", "password": "secret123", "name": "Asha"}'

# set a wishlist (use the id returned by signup)
curl -b cookies.txt -X PATCH http://127.0.0.1:8000/participant/2/wishlist \
  -H "Content-Type: application/json" \
  -d '{"wishlist": "notebooks, green tea"}'

# log in as the admin and run the draw (needs 3 or more participants)
curl -c admin.txt -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "<superuser>", "password": "<password>"}'
curl -b admin.txt -X POST http://127.0.0.1:8000/draw/run

# each participant checks their own giftee
curl -b cookies.txt http://127.0.0.1:8000/my-giftee
```

## How the draw works

The logic is in `santa/draw.py`. The participants are shuffled into a random order, and each person gives to the next person in that order. The last person gives to the first. That makes one big circle, so:

- nobody is assigned to themselves
- everyone gives to exactly one person and receives from exactly one person
- no two people are paired with each other, as long as there are 3 or more people

With only 2 people a mutual pair cannot be avoided, which is why the draw needs at least 3 participants (set by `MIN_PARTICIPANTS` in `settings.py`).

The draw runs inside a database transaction, so it either fully completes or nothing is saved.

## How the code is organised

- `secretsanta/` holds the project settings and the root urls.
- `santa/models.py` has two models. `Participant` extends Django's built-in `User` with a wishlist and a `giftee`. `DrawState` is a single row that remembers whether the draw is locked or has run.
- `santa/views.py` has one function per endpoint. Two small decorators, `login_needed` and `admin_needed`, return JSON errors instead of redirects.
- `santa/draw.py` is the pairing logic, kept separate so it can be tested on its own.
- `santa/tests.py` covers the draw, privacy, locking, wishlists and admin actions.

Privacy is enforced in the views, not only in the interface. `/my-giftee` always looks up the logged-in user's own record, and the profile and wishlist endpoints compare the id in the url with the logged-in user.

## Design notes

- Assignments are stored on the participant row (`giftee`). There is no endpoint that returns all of them.
- `/my-wishlist-giver` only says whether you have a gifter. Returning the name would break the secret, so I chose not to.
- Admin rights come from Django's `is_staff` flag, so there is no shared key in the source code.
- Plain Django views with `JsonResponse` are used instead of Django REST Framework to keep the project small.

## Known limitations

- The state-changing endpoints are exempt from CSRF checks (`@csrf_exempt`) because this is a JSON API with no HTML forms. For a real deployment with browser clients, I would switch to token authentication (for example JWT) or turn CSRF protection back on.
- SQLite is used for simplicity. PostgreSQL would be the choice for production.
- There is no rate limiting on login.
- `SECRET_KEY` and `DEBUG` in `settings.py` are development values and should come from environment variables when deploying.
