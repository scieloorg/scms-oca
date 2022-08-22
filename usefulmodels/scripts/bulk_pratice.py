import os
from usefulmodels import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of pratices
# Consider that existe a user with id=1

PRATICES = [
    ('100', 'menção genérica à CA ou todas as práticas'),
    ('210', 'preprints'),
    ('220', 'version of record indexados - periódicos, documentos, artigos'),
    ('230', 'livros, capítulo de livros'),
    ('240', 'teses, dissertações, TCC'),
    ('250', 'projetos de pesquisa'),
    ('260', 'declarações'),
    ('270', 'outros docs'),
    ('280', 'repositórios tipo verde – documentos em geral, ..'),
    ('300', 'dados genéricos'),
    ('310', 'códigos'),
    ('400', 'peer review'),
    ('500', 'ciência cidadã'),
    ('600', 'recursos educacionais'),
    ('900', 'outra'),
]

def run(*args):
    user_id = 1

    # Delete all pratices
    models.Pratice.objects.all().delete()

    # User
    if args:
        user_id = args[0]

    creator = User.objects.get(id=user_id)

    for code, val in PRATICES:

        models.Pratice(code=code, name=val, creator=creator).save()
