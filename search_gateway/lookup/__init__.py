from search_gateway.lookup.base import LookupBuilder
from search_gateway.lookup.builders import (
    DocumentLanguageLookupBuilder,
    FunderLookupBuilder,
    InstitutionLookupBuilder,
    PublisherLookupBuilder,
    SourceLookupBuilder,
    TopicLookupBuilder,
)

LOOKUP_BUILDERS: dict[str, type[LookupBuilder]] = {
    DocumentLanguageLookupBuilder.key: DocumentLanguageLookupBuilder,
    FunderLookupBuilder.key: FunderLookupBuilder,
    InstitutionLookupBuilder.key: InstitutionLookupBuilder,
    PublisherLookupBuilder.key: PublisherLookupBuilder,
    SourceLookupBuilder.key: SourceLookupBuilder,
    TopicLookupBuilder.key: TopicLookupBuilder,
}

DEFAULT_LOOKUPS: list[str] = [
    InstitutionLookupBuilder.key,
    FunderLookupBuilder.key,
    PublisherLookupBuilder.key,
    SourceLookupBuilder.key,
    TopicLookupBuilder.key,
    DocumentLanguageLookupBuilder.key,
]
