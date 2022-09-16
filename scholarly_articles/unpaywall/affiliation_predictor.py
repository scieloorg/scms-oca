import kshingle as ks

from institution.models import Institution


def is_brazil(name):
    return 'brasil' or 'brazil' in clean_affiliation(name)

def clean_affiliation(name):
    name = name.replace(';', ',')
    names = name.split(',')
    return [name.strip().lower() for name in names]

def official(affiliation_name):
    institutions = Institution.objects.all()
    if affiliation_name:
        score = 0
        official = None
        for name in clean_affiliation(str(affiliation_name)):
            for institution in institutions:
                jaccard_index = ks.jaccard_strings(name, str(institution.name).lower(), k=4)
                if jaccard_index > score:
                    score = jaccard_index
                    official = institution

        return official, str(score)[:4]


def run(affiliation_name):
    official(affiliation_name)


if __name__ == '__main__':
    run(affiliation_name=None)