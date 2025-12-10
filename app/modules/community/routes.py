from flask import render_template, redirect, url_for, flash, jsonify, request, current_app
from app import db
from app.modules.community import community_bp
from app.modules.community.models import Community
from app.modules.community.forms import CommunityForm
from flask_login import login_required, current_user
from app.modules.notifications.models import user_follows_community
from app.extensions import db as extensions_db


@community_bp.route('/community/list', methods=['GET', 'POST'])
@login_required
def list_communities():
    comunities = Community.query.all()
    return render_template('community/list_communities.html', communities=comunities)


@community_bp.route('/community/create', methods=['GET', 'POST'])
@login_required
def create_community():
    form = CommunityForm()
    if form.validate_on_submit():
        new_community = Community(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(new_community)
        db.session.commit()
        flash('Community created successfully!', 'success')
        return redirect(url_for('public.index'))
    return render_template("community/create.html", form=form)


@community_bp.route('/community/join/<int:community_id>', methods=['POST'])
@login_required
def join_community(community_id):
    community = Community.query.get_or_404(community_id)
    if current_user not in community.community_members:
        community.community_members.append(current_user)
        db.session.commit()
        flash(f'You have joined the community: {community.name}', 'success')
        current_app.logger.info(f"User {current_user.id} joined community {community.id}")
        # If this is an AJAX request, return JSON instead of redirecting
        # If the client expects JSON (Accept: application/json), return JSON for AJAX calls
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept:
            return jsonify({"message": "Joined", "member": True, "community_id": community.id})
    else:
        flash('You are already a member of this community.', 'info')
    # After joining, return to the community page so the user sees the updated state
    return redirect(url_for('community.view_community', community_id=community.id))


@community_bp.route('/community/leave/<int:community_id>', methods=['POST'])
@login_required
def leave_community(community_id):
    community = Community.query.get_or_404(community_id)
    if current_user in community.community_members:
        try:
            community.community_members.remove(current_user)
            db.session.commit()
            flash(f'You have left the community: {community.name}', 'success')
            current_app.logger.info(f"User {current_user.id} left community {community.id}")
            accept = request.headers.get('Accept', '')
            if 'application/json' in accept:
                return jsonify({"message": "Left", "member": False, "community_id": community.id})
        except Exception:
            db.session.rollback()
            flash('Could not leave the community. Please try again.', 'danger')
    else:
        flash('You are not a member of this community.', 'info')
    # After leaving, return to the community page so the user can join again
    return redirect(url_for('community.view_community', community_id=community.id))


@community_bp.route('/community/<int:community_id>', methods=['GET'])
@login_required
def view_community(community_id):
    comunnity = Community.query.get_or_404(community_id)
    # Determine if current user follows this community so the template
    # can render the correct button state on load.
    is_following = False
    try:
        if current_user.is_authenticated:
            exists = (
                extensions_db.session.query(user_follows_community)
                .filter(user_follows_community.c.user_id == current_user.id)
                .filter(user_follows_community.c.community_id == comunnity.id)
                .first()
            )
            is_following = bool(exists)
    except Exception:
        is_following = False

    # Build join/leave URLs defensively: url_for can raise BuildError in some dev reload states,
    # so fall back to literal paths if resolution fails.
    join_url = f"/community/join/{comunnity.id}"
    leave_url = f"/community/leave/{comunnity.id}"
    try:
        join_url = url_for('community.join_community', community_id=comunnity.id)
    except Exception:
        pass
    try:
        leave_url = url_for('community.leave_community', community_id=comunnity.id)
    except Exception:
        pass

    return render_template(
        'community/view_community.html',
        community=comunnity,
        is_following=is_following,
        join_url=join_url,
        leave_url=leave_url,
    )
