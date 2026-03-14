from flask import Blueprint, render_template

from app.analyzer import get_insights

insights_bp = Blueprint('insights', __name__)


@insights_bp.route('/')
def index():
    insights = get_insights()

    recurring = [i for i in insights if i.insight_type == 'recurring_peak']
    correlations = [i for i in insights if i.insight_type == 'correlation']
    recommendations = [i for i in insights if i.insight_type == 'recommendation']

    return render_template(
        'insights.html',
        recurring=recurring,
        correlations=correlations,
        recommendations=recommendations,
    )
