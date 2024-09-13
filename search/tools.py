from article.choices import DOCUMENT_TYPE
from django.utils.translation import gettext as _


def normalize_dictionary(dictionary, static_list=DOCUMENT_TYPE):
    """Normalized a dictionary of licenses, grouping unmatched entries under 'others'.

    Args:
        dictionary (dict): The dictionary of licenses.
        static_list (list): The list of valid static_list.

    Returns:
        dict: The normalized dictionary.
    """

    normalized_dict = {}
    others = []

    for key, value in dictionary.items():
        normalized_key = key.upper()
        if any(normalized_key in item for item in static_list):
            normalized_dict[key] = value
        else:
            others.extend(value)

    if others:
        normalized_dict["others"] = others

    return normalized_dict

def remove_term(text, term):
    """
    Removes the specified term from the given text.

    Args:
        text: The input text string.
        term: The term to be removed from the text.

    Returns:
        The modified text with the term removed.
    """

    # Check if the term exists in the text (case-insensitive)
    if term.lower() in text.lower():
        # Split the text into words
        words = text.split()

        # Remove the matching term (case-insensitive)
        filtered_words = [word for word in words if word.lower() != term.lower()]

        # Join the remaining words back into a string
        modified_text = " ".join(filtered_words)

        return modified_text
    else:
        # Return the original text if the term is not found
        return text


def generate_string(
    terms,
    year_range,
    inicial_text = _("Evolução anual da"),
    medium_text = _("distribuição da produção científica"),
    preposition_text = _("por "),
    prol_text = ""
):
    """
    Generates a custom string based on a list of terms and a year range.

    Args:
    terms: A list of terms to be concatenated.
    year_range: A tuple representing the year range (start_year, end_year).

    Returns:
    A formatted string according to the specification.
    """
    if len(terms) > 1:
        terms_str = preposition_text + ", ".join(terms[:-1]) + prol_text +  _(" no ") + terms[-1]
    else:
        terms_str = "no %s" % terms[0]

    if year_range[0] == year_range[1]:
        inicial_text = _("Distribuição")
        medium_text = _("da produção científica")
        years_str = year_range[0]
    else:
        # Formats the year range
        years_str = f"{year_range[0]}-{year_range[1]}"
    # Concatenates all parts of the string
    
    final_string = f"{inicial_text} {medium_text} {terms_str}, {years_str}"

    return final_string
