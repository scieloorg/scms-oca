from article.choices import LICENSE

def normalize_dictionary(dictionary, licenses=LICENSE):
    """Normalized a dictionary of licenses, grouping unmatched entries under 'others'.

    Args:
        dictionary (dict): The dictionary of licenses.
        licenses (list): The list of valid licenses.

    Returns:
        dict: The normalized dictionary.
    """

    normalized_dict = {}
    others = []

    for key, value in dictionary.items():
        normalized_key = key.replace(" ", "-").upper()
        if any(normalized_key in license for license in licenses):
            normalized_dict[key] = value
        else:
            others.extend(value)

    if others:
        normalized_dict['others'] = others

    return normalized_dict