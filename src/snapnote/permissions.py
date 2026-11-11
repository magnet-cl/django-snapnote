def is_authenticated(user):
    return bool(user and user.is_authenticated)
