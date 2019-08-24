def update_model(instance, **kwargs):
    for k, v in kwargs.items():
        if __has_field(instance, k):
            setattr(instance, k, v)
    return instance


def __has_field(instance, name):
    for field in instance._meta.get_fields():
        if field.name == name:
            return True
    return False
