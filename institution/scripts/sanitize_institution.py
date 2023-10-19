from institution.tasks import sanitize_institutions

def run(user_id):
    sanitize_institutions(user_id)
