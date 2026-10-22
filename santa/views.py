import json
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .draw import make_pairs
from .models import DrawState, Participant


def error(message, status):
    return JsonResponse({"error": message}, status=status)


def read_json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def login_needed(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error("login required", 401)
        return view(request, *args, **kwargs)

    return wrapper


def admin_needed(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error("login required", 401)
        if not request.user.is_staff:
            return error("admin only", 403)
        return view(request, *args, **kwargs)

    return wrapper


def current_participant(request):
    # admins made with createsuperuser are not participants, so this can be None
    return Participant.objects.filter(user=request.user).first()


# ---------- auth ----------

@csrf_exempt
@require_POST
def signup(request):
    data = read_json(request)
    if data is None:
        return error("body must be valid json", 400)

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    wishlist = str(data.get("wishlist", "")).strip()

    if not username or len(password) < 8:
        return error("username is required and password needs 8+ characters", 400)
    if len(wishlist) > settings.MAX_WISHLIST_LENGTH:
        return error(f"wishlist is limited to {settings.MAX_WISHLIST_LENGTH} characters", 400)
    if DrawState.get().locked:
        return error("signups are closed", 403)
    if User.objects.filter(username=username).exists():
        return error("username already taken", 409)

    user = User.objects.create_user(
        username=username, email=email, password=password, first_name=name
    )
    participant = Participant.objects.create(user=user, wishlist=wishlist)
    login(request, user)
    return JsonResponse({"id": user.id, "name": participant.display_name()}, status=201)


@csrf_exempt
@require_POST
def login_view(request):
    data = read_json(request)
    if data is None:
        return error("body must be valid json", 400)

    user = authenticate(
        request,
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
    )
    if user is None:
        return error("wrong username or password", 401)

    login(request, user)
    return JsonResponse({"id": user.id, "is_admin": user.is_staff})


@csrf_exempt
@require_POST
@login_needed
def logout_view(request):
    logout(request)
    return JsonResponse({"message": "logged out"})


# ---------- draw ----------

@require_GET
def draw_status(request):
    state = DrawState.get()
    return JsonResponse({
        "participants": Participant.objects.count(),
        "minimum_needed": settings.MIN_PARTICIPANTS,
        "locked": state.locked,
        "drawn": state.drawn,
    })


@csrf_exempt
@require_POST
@admin_needed
def run_draw(request):
    with transaction.atomic():
        state = DrawState.get()
        if state.drawn:
            return error("the draw has already been run", 409)

        people = list(Participant.objects.all())
        if len(people) < settings.MIN_PARTICIPANTS:
            return error(
                f"need at least {settings.MIN_PARTICIPANTS} participants, have {len(people)}",
                400,
            )

        for giver, giftee in make_pairs(people):
            giver.giftee = giftee
            giver.save()

        state.drawn = True
        state.locked = True
        state.drawn_at = timezone.now()
        state.save()

    return JsonResponse({"message": "draw complete", "participants": len(people)})


@csrf_exempt
@require_POST
@admin_needed
def lock_draw(request):
    # closes signups without running the draw. the draw can still be run later
    state = DrawState.get()
    state.locked = True
    state.save()
    return JsonResponse({"locked": True, "drawn": state.drawn})


# ---------- participants ----------

@require_GET
@login_needed
def participants(request):
    people = Participant.objects.select_related("user").order_by("joined_at")
    return JsonResponse({
        "participants": [{"id": p.pk, "name": p.display_name()} for p in people]
    })


@csrf_exempt
@login_needed
def participant_detail(request, user_id):
    if request.method == "GET":
        return show_profile(request, user_id)
    if request.method == "DELETE":
        return delete_participant(request, user_id)
    return error("method not allowed", 405)


def show_profile(request, user_id):
    me = current_participant(request)
    if me is None or me.pk != user_id:
        return error("you can only view your own profile", 403)
    return JsonResponse({
        "id": me.pk,
        "username": request.user.username,
        "name": me.display_name(),
        "email": request.user.email,
        "wishlist": me.wishlist,
    })


def delete_participant(request, user_id):
    if not request.user.is_staff:
        return error("admin only", 403)
    if DrawState.get().drawn:
        return error("cannot remove people after the draw", 409)

    person = Participant.objects.filter(pk=user_id).first()
    if person is None:
        return error("participant not found", 404)

    person.user.delete()  # also deletes the participant row
    return JsonResponse({"message": "participant removed"})


@csrf_exempt
@login_needed
def update_wishlist(request, user_id):
    if request.method != "PATCH":
        return error("method not allowed", 405)

    me = current_participant(request)
    if me is None or me.pk != user_id:
        return error("you can only edit your own wishlist", 403)

    data = read_json(request)
    if data is None or "wishlist" not in data:
        return error("send a json body with a wishlist field", 400)

    wishlist = str(data["wishlist"]).strip()
    if len(wishlist) > settings.MAX_WISHLIST_LENGTH:
        return error(f"wishlist is limited to {settings.MAX_WISHLIST_LENGTH} characters", 400)

    me.wishlist = wishlist
    me.save()
    return JsonResponse({"wishlist": me.wishlist})


# ---------- private views ----------

@require_GET
@login_needed
def my_giftee(request):
    me = current_participant(request)
    if me is None:
        return error("you are not a participant", 404)
    if me.giftee is None:
        return error("the draw has not been run yet", 404)

    # only the name and wishlist, never an id or anything about other pairings
    return JsonResponse({
        "giftee": {"name": me.giftee.display_name(), "wishlist": me.giftee.wishlist}
    })


@require_GET
@login_needed
def my_wishlist_giver(request):
    me = current_participant(request)
    if me is None:
        return error("you are not a participant", 404)

    # this tells you that someone has you, not who. revealing the name would
    # break the secret
    return JsonResponse({
        "draw_done": DrawState.get().drawn,
        "has_gifter": Participant.objects.filter(giftee=me).exists(),
        "my_wishlist": me.wishlist,
    })
