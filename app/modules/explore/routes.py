from flask import jsonify, render_template, request

from app.modules.community.models import Community
from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        communities = Community.query.all()
        query = request.args.get("query", "")
        form = ExploreForm()
        return render_template("explore/index.html", form=form, query=query, communities=communities)

    if request.method == "POST":
        criteria = request.get_json()
        datasets = ExploreService().filter(**criteria)
        return jsonify([dataset.to_dict() for dataset in datasets])
