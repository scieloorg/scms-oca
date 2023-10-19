
from config.settings.base import env
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe


# Directory helps:

DIRECTORY_TITLE_HELP = env.str("DIRECTORY_TITLE_HELP", default=mark_safe(_('Título do item, veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#title" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#title</a>')))

DIRECTORY_LINK_HELP = env.str("DIRECTORY_LINK_HELP", default=mark_safe(_('Link URL do item específico, veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#link" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#link</a>')))

DIRECTORY_DESCRIPTION_HELP = env.str("DIRECTORY_DESCRIPTION_HELP", default=mark_safe(_('Descrição/representação do item, veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#descri%C3%A7%C3%A3o" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#descri%C3%A7%C3%A3o</a>')))

DIRECTORY_SOURCE_HELP = env.str("DIRECTORY_SOURCE_HELP", default=mark_safe(_('Instituição a qual o item é subordinado (quando houver). É diferente da instituição. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#origem" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#origem</a>')))

DIRECTORY_INSTITUTIONS_HELP = env.str("DIRECTORY_INSTITUTIONS_HELP", default=mark_safe(_('Instituição/empresa ao qual o item registrado pertence. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#institui%C3%A7%C3%A3o" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#institui%C3%A7%C3%A3o</a>')))

DIRECTORY_THEMATIC_AREA_HELP = env.str("DIRECTORY_THEMATIC_AREA_HELP", default=mark_safe(_('Grandes área do conhecimento ao qual pertence o item. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#%C3%A1rea-tem%C3%A1tica" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#%C3%A1rea-tem%C3%A1tica</a>')))

DIRECTORY_KEYWORDS_AREA_HELP = env.str("DIRECTORY_KEYWORDS_AREA_HELP", default=mark_safe(_('Palavras-chaves do item. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#palavras-chaves" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#palavras-chaves</a>')))

DIRECTORY_PRACTICE_HELP = env.str("DIRECTORY_PRACTICE_HELP", default=mark_safe(_('Prática da ciência aberta referente ao item registrado. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#pr%C3%A1tica" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#pr%C3%A1tica</a>')))

DIRECTORY_ACTION_HELP = env.str("DIRECTORY_ACTION_HELP", default=mark_safe(_('')))

DIRECTORY_CLASSIFICATION_HELP = env.str("DIRECTORY_CLASSIFICATION_HELP", default=mark_safe(_('Classificação referente ao item registrado. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#classifica%C3%A7%C3%A3o" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#classifica%C3%A7%C3%A3o</a>')))

DIRECTORY_RECORD_STATUS_HELP = env.str("DIRECTORY_RECORD_STATUS_HELP", default=mark_safe(_('Status do registro no OCABR. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#status" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#status</a>')))

DIRECTORY_NOTES_HELP = env.str("DIRECTORY_NOTES_HELP", default=mark_safe(_('Anotações sobre o registro. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#notes" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#notes</a>')))

DIRECTORY_INSTITUTIONAL_CONTRIBUTION_HELP = env.str("DIRECTORY_INSTITUTIONAL_CONTRIBUTION_HELP", default=mark_safe(_('Nome da instituição que contribuiu. Veja exemplo em: <a href="https://github.com/scieloorg/scms-oca/wiki/Campos#institui%C3%A7%C3%A3o-contribuidora" target="_blank">https://github.com/scieloorg/scms-oca/wiki/Campos#institui%C3%A7%C3%A3o-contribuidora</a>')))
