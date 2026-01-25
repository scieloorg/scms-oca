import inspect
import logging
from datetime import datetime

from lxml import etree

from .exception_logs import ExceptionContext
from .utils import parse_author_name

namespaces = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

def get_info_article(rec, exc_context, nodes):
    NODES = nodes
    article_dict = {}
    root = etree.fromstring(str(rec))

    for node in NODES:
        article_dict[node] = []
        for x in root.xpath(f".//dc:{node}", namespaces=namespaces):
            node_dict = {"text": x.text}
            lang = x.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang:
                node_dict["lang"] = lang
            article_dict[node].append(node_dict)
    
    article_dict["language"] = get_language_node(
        root=root, exc_context=exc_context
    )
    article_dict["date"] = get_date(root=root, exc_context=exc_context)
    article_dict["authors"] = get_name_author(root=root, exc_context=exc_context)
    article_dict["source"] = get_identifier_source(
        root=root, exc_context=exc_context
    )
    return article_dict


def get_language_node(root, exc_context: ExceptionContext):
    try:
        return root.xpath(".//dc:language", namespaces=namespaces)[0].text
    except IndexError as e:
        logging.warning(
            f"Exception in {inspect.stack()[0].function}: {e}",
            extra={'field': "language"}
        )
        exc_context.add_exception(
            exception=e,
            field_name="language",
        )


def get_identifier_source(root, exc_context: ExceptionContext):
    identifiers = root.xpath(".//dc:identifier", namespaces=namespaces)
    urls = []
    for identifier in identifiers:
        if not identifier.text:
            continue
        text = identifier.text.strip()
        if text.startswith("http://") or text.startswith("https://"):
            urls.append(text)

    return urls

def get_date(root, exc_context: ExceptionContext):
    try:
        date_string = root.xpath(".//dc:date", namespaces=namespaces)[0].text
        date = datetime.strptime(date_string, "%Y-%m-%d")
        return {
            "day": date.day,
            "month": date.month,
            "year": date.year,
        }
    except ValueError as e:
        logging.warning(
            f"Exception in {inspect.stack()[0].function}: {e}",
            extra={'raw': date_string}
        )
        exc_context.add_exception(
            exception=ValueError("Invalid date"),
            field_name="date",
        )
    except IndexError as e:
        logging.warning(
            f"Exception in {inspect.stack()[0].function}: {e}",
        )
        exc_context.add_exception(
            exception=IndexError("Error retrieving preprint data."),
            field_name="date",
        )
def get_name_author(root, exc_context: ExceptionContext):
    author_data = []
    for author in root.xpath(".//dc:creator", namespaces=namespaces):
        try:
            name_author = author.text.strip()
            author_dict = parse_author_name(name_author)
            author_data.append(author_dict)
        except Exception as e:
            logging.warning(
                f"Exception in {inspect.stack()[0].function}: {e}",
                extra={'field': "creator"}
            )
            exc_context.add_exception(
                exception=e,
                field_name="creator",
                context={"name_creator": name_author}
            )            
    return author_data
