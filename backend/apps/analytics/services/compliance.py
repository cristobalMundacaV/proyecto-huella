def create_compliance_entity(model, data):
    return model.objects.create(**data)


def update_compliance_entity(instance, data):
    for field, value in data.items():
        setattr(instance, field, value)
    instance.save()
    return instance


def delete_compliance_entity(instance):
    instance.delete()
