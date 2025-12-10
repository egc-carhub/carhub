from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.modules.auth.services import AuthenticationService
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet
from app.modules.profile import profile_bp
from app.modules.profile.forms import UserProfileForm
from app.modules.profile.services import UserProfileService
from app.modules.notifications.models import user_follows_user
from app.extensions import db as extensions_db


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    auth_service = AuthenticationService()
    profile = auth_service.get_authenticated_user_profile
    if not profile:
        return redirect(url_for("public.index"))

    form = UserProfileForm()
    if request.method == "POST":
        service = UserProfileService()
        result, errors = service.update_profile(profile.id, form)
        return service.handle_service_response(
            result, errors, "profile.edit_profile", "Profile updated successfully", "profile/edit.html", form
        )

    return render_template("profile/edit.html", form=form)


@profile_bp.route("/profile/summary")
@login_required
def my_profile():
    page = request.args.get("page", 1, type=int)
    per_page = 5

    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == current_user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_datasets_count = db.session.query(DataSet).filter(DataSet.user_id == current_user.id).count()

    print(user_datasets_pagination.items)

    return render_template(
        "profile/summary.html",
        user_profile=current_user.profile,
        user=current_user,
        datasets=user_datasets_pagination.items,
        pagination=user_datasets_pagination,
        total_datasets=total_datasets_count,
    )


@profile_bp.route("/profile/<int:user_id>")
def user_profile(user_id):
    """Public view of a user's profile and their uploaded datasets."""
    page = request.args.get("page", 1, type=int)
    per_page = 5

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("public.index"))

    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_datasets_count = db.session.query(DataSet).filter(DataSet.user_id == user.id).count()
    # Determine if the current authenticated user follows this user so the template
    # can render the correct follow/unfollow label on page load.
    is_following = False
    try:
        from flask_login import current_user as _current_user

        if _current_user.is_authenticated:
            exists = (
                extensions_db.session.query(user_follows_user)
                .filter(user_follows_user.c.follower_id == _current_user.id)
                .filter(user_follows_user.c.followed_id == user.id)
                .first()
            )
            is_following = bool(exists)
    except Exception:
        # Non-fatal: if something goes wrong reading the follow table, default to False.
        is_following = False

    return render_template(
        "profile/summary.html",
        user_profile=user.profile,
        user=user,
        datasets=user_datasets_pagination.items,
        pagination=user_datasets_pagination,
        total_datasets=total_datasets_count,
        is_following=is_following,
    )
