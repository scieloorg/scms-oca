import re
from dataclasses import dataclass

from django.utils.translation import gettext as _

from search.choices import QUERY_STRING_FIELD_ALIASES


OPERATORS = {"AND", "OR", "NOT"}
VALUE_TOKEN_TYPES = {"TERM", "PHRASE"}
INCOMPLETE_FIELD_FOLLOWERS = {None, "OPERATOR", "FIELD", ")"}
INCOMPLETE_EXPRESSION_PREVIOUS_TYPES = {"FIELD", "OPERATOR", "("}


class AdvancedQueryValidationError(ValueError):
    """Raised when the user-provided advanced search expression is invalid."""


@dataclass(frozen=True)
class Token:
    type: str
    value: str


def _allowed_advanced_query_fields():
    return set(QUERY_STRING_FIELD_ALIASES) | set(QUERY_STRING_FIELD_ALIASES.values())


def _normalize_field_name(field_name):
    return QUERY_STRING_FIELD_ALIASES.get(field_name.lower(), field_name)


def _raise_missing_operator_error():
    raise AdvancedQueryValidationError(
        _("Use AND, OR ou NOT para combinar termos na busca avançada.")
    )


class AdvancedQueryTokenizer:
    field_pattern = re.compile(r"([A-Za-z_][\w.]*)\s*:")
    term_pattern = re.compile(r"[^\s()]+")

    def __init__(self, query_text):
        self.query_text = query_text or ""
        self.index = 0

    def tokenize(self):
        tokens = []
        while not self._is_finished():
            token = self._read_next_token()
            if token is not None:
                tokens.append(token)
        return tokens

    def _is_finished(self):
        return self.index >= len(self.query_text)

    def _read_next_token(self):
        char = self.query_text[self.index]

        if char.isspace():
            self.index += 1
            return None
        if char == '"':
            return self._read_phrase()
        if char in "()":
            self.index += 1
            return Token(char, char)

        field_token = self._read_field()
        if field_token is not None:
            return field_token
        return self._read_term()

    def _read_phrase(self):
        start = self.index
        self.index += 1
        escaped = False

        while not self._is_finished():
            current = self.query_text[self.index]
            if current == "\\" and not escaped:
                escaped = True
                self.index += 1
                continue
            if current == '"' and not escaped:
                self.index += 1
                return Token("PHRASE", self.query_text[start:self.index])
            escaped = False
            self.index += 1

        raise AdvancedQueryValidationError(
            _("A busca avançada contém aspas sem fechamento.")
        )

    def _read_field(self):
        match = self.field_pattern.match(self.query_text, self.index)
        if not match:
            return None
        self.index = match.end()
        return Token("FIELD", match.group(1))

    def _read_term(self):
        match = self.term_pattern.match(self.query_text, self.index)
        if not match:
            self.index += 1
            return None

        term = match.group(0)
        self.index = match.end()
        operator = term.upper()
        if operator in OPERATORS:
            return Token("OPERATOR", operator)
        return Token("TERM", term)


class AdvancedQueryNormalizer:
    def __init__(self, tokens):
        self.tokens = tokens
        self.allowed_fields = _allowed_advanced_query_fields()
        self.parts = []
        self.parentheses_depth = 0
        self.expect_operand = True
        self.previous_type = None
        self.index = 0

    def normalize(self):
        while not self._is_finished():
            self._consume_current_token()

        self._validate_final_state()
        return " ".join(self.parts)

    def _is_finished(self):
        return self.index >= len(self.tokens)

    def _current_token(self):
        return self.tokens[self.index]

    def _next_type(self):
        if self.index + 1 >= len(self.tokens):
            return None
        return self.tokens[self.index + 1].type

    def _advance(self, steps=1):
        self.index += steps

    def _consume_current_token(self):
        token = self._current_token()
        handlers = {
            "FIELD": self._consume_field,
            "OPERATOR": self._consume_operator,
            "(": self._consume_open_parenthesis,
            ")": self._consume_close_parenthesis,
        }
        handler = handlers.get(token.type, self._consume_standalone_value)
        handler(token)

    def _consume_field(self, token):
        if not self.expect_operand:
            _raise_missing_operator_error()

        self._validate_field_name(token.value)
        self._validate_field_has_value(token.value)

        if self._next_type() == "(":
            self._consume_grouped_field(token.value)
            return

        value_tokens = self._collect_field_value_tokens()
        self.parts.append(
            f"{_normalize_field_name(token.value)}:{self._format_field_value(value_tokens)}"
        )
        self.expect_operand = False
        self.previous_type = "TERM"

    def _validate_field_name(self, field_name):
        if field_name.lower() in self.allowed_fields:
            return
        raise AdvancedQueryValidationError(
            _(f"Campo desconhecido na busca avançada: {field_name}")
        )

    def _validate_field_has_value(self, field_name):
        if self._next_type() not in INCOMPLETE_FIELD_FOLLOWERS:
            return
        raise AdvancedQueryValidationError(
            _(f"Informe um termo após o campo {field_name}.")
        )

    def _consume_grouped_field(self, field_name):
        self.parentheses_depth += 1
        self.parts.append(f"{_normalize_field_name(field_name)}:(")
        self.expect_operand = True
        self.previous_type = "("
        self._advance(2)

    def _collect_field_value_tokens(self):
        value_tokens = []
        self._advance()
        while not self._is_finished() and self._current_token().type in VALUE_TOKEN_TYPES:
            value_tokens.append(self._current_token())
            self._advance()
        return value_tokens

    def _format_field_value(self, value_tokens):
        if len(value_tokens) == 1:
            return value_tokens[0].value
        return f"({' '.join(token.value for token in value_tokens)})"

    def _consume_operator(self, token):
        if token.value in {"AND", "OR"} and self.expect_operand:
            raise AdvancedQueryValidationError(
                _("Operador %(operator)s em posição inválida.")
                % {"operator": token.value}
            )
        if token.value == "NOT" and self._next_type() in {None, "OPERATOR", ")"}:
            raise AdvancedQueryValidationError(
                _("Informe um termo após o operador NOT.")
            )

        self.parts.append(token.value)
        self.expect_operand = True
        self.previous_type = token.type
        self._advance()

    def _consume_open_parenthesis(self, token):
        if not self.expect_operand:
            _raise_missing_operator_error()
        if self._next_type() == ")":
            raise AdvancedQueryValidationError(
                _("A busca avançada contém parênteses vazios.")
            )

        self.parentheses_depth += 1
        self.parts.append(token.value)
        self.expect_operand = True
        self.previous_type = token.type
        self._advance()

    def _consume_close_parenthesis(self, token):
        self.parentheses_depth -= 1
        if self.parentheses_depth < 0:
            raise AdvancedQueryValidationError(
                _("A busca avançada contém parêntese de fechamento sem abertura.")
            )
        if self.expect_operand or self.previous_type in INCOMPLETE_EXPRESSION_PREVIOUS_TYPES:
            raise AdvancedQueryValidationError(
                _("A busca avançada contém uma expressão incompleta antes de ')'.")
            )

        self.parts.append(token.value)
        self.expect_operand = False
        self.previous_type = token.type
        self._advance()

    def _consume_standalone_value(self, token):
        if not self.expect_operand:
            _raise_missing_operator_error()

        self.parts.append(token.value)
        self.expect_operand = False
        self.previous_type = token.type
        self._advance()

    def _validate_final_state(self):
        if self.parentheses_depth:
            raise AdvancedQueryValidationError(
                _("A busca avançada contém parênteses sem fechamento.")
            )
        if self.expect_operand or self.previous_type in INCOMPLETE_EXPRESSION_PREVIOUS_TYPES:
            raise AdvancedQueryValidationError(
                _("A busca avançada termina com uma expressão incompleta.")
            )


def normalize_advanced_query(query_text):
    cleaned_query = (query_text or "").strip()
    if not cleaned_query:
        return ""

    tokens = AdvancedQueryTokenizer(cleaned_query).tokenize()
    if not tokens:
        return ""
    return AdvancedQueryNormalizer(tokens).normalize()


def validate_advanced_query(query_text):
    normalize_advanced_query(query_text)
