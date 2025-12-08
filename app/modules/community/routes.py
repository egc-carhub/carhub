from flask import render_template, redirect, url_for, flash
from app import db
from app.modules.community import community_bp
from app.modules.community.models import Community
from app.modules.community.forms import CommunityForm
from flask_login import login_required, current_user


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
        flash('You have joined the community: {community.name}', 'success')
    else:
        flash('You are already a member of this community.', 'info')
    return redirect(url_for('community.list_communities'))


@community_bp.route('/community/<int:community_id>', methods=['GET'])
@login_required
def view_community(community_id):
    comunnity = Community.query.get_or_404(community_id)
    return render_template('community/view_community.html', community=comunnity)
