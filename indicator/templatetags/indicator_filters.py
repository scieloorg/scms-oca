from django import template

register = template.Library()


@register.filter
def stz_filter(value):
    if not value:
        return value
    
    # Convert boolean strings to Yes/No
    if str(value).lower() == 'true':
        return 'Yes'
    elif str(value).lower() == 'false':
        return 'No'
    
    # Words that should remain in UPPERCASE
    uppercase_words = {
        'cwts', 'sjr', 'snip', 'issn', 'apc', 'usd', 'sdg', 'doi', 'api', 'url', 'id'
    }
    
    # Words that should remain in lowercase (prepositions, articles, conjunctions)
    lowercase_words = {
        # English
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 
        'into', 'of', 'on', 'or', 'the', 'to', 'with', 'is', 'are', 'vs',
        # Portuguese
        'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
        'do', 'da', 'dos', 'das', 'de', 'em', 'no', 'na', 'nos', 'nas',
        'ao', 'à', 'aos', 'às', 'por', 'para', 'com', 'sem', 'sob', 'sobre'
    }
    
    # Replace underscores with spaces
    words = value.replace('_', ' ').split()
    
    # Apply casing rules
    result = []

    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # First word is always capitalized (unless it's an acronym)
        if i == 0:
            if word_lower in uppercase_words:
                result.append(word.upper())
            else:
                result.append(word.capitalize())

        # Check if word should be uppercase (acronyms)
        elif word_lower in uppercase_words:
            result.append(word.upper())

        # Check if word should be lowercase (prepositions)
        elif word_lower in lowercase_words:
            result.append(word_lower)

        # Capitalize other words
        else:
            result.append(word.capitalize())
    
    return ' '.join(result)
