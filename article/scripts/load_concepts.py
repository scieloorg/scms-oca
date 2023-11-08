import pandas as pd
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article.tasks import load_concepts

User = get_user_model()


def run(user_id):
    """
    Load the concepts from a csv file.
    """
    load_concepts.apply_async(args=(int(user_id),))
    