def normalize_key(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace("/", " ")
        .replace("-", " ")
    )


def unique_code(model, field, base, pk=None, limit=80):
    root = (normalize_key(base).upper().replace(" ", "_") or model.__name__.upper())[
        :limit
    ]
    candidate = root
    suffix = 2
    while model.objects.filter(**{field: candidate}).exclude(pk=pk).exists():
        candidate = f"{root[: limit - len(str(suffix)) - 1]}_{suffix}"
        suffix += 1
    return candidate
