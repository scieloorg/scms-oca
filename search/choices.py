from django.utils.translation import gettext as _

translates = {
    "all": _("Todos"),
    "ocabr": _("OCABr"),
    "document": _("Produção científica"),
    "openalex": _("OpenAlex"),
    "ocabr+openalex": _("OCABr + OpenAlex"),
    "education_directory": _("Educação"),
    "event_directory": _("Disseminação"),
    "infrastructure_directory": _("Infraestrutura"),
    "policy_directory": _("Política"),
    "record_type": _("tipo de registro"),
    "directory_type": _("dados"),
    "countries": _("país"),
    "states": _("estado"),
    "cities": _("cidade"),
    "regions": _("região"),
    "brazil_posgraduate": _("Pós-Graduação"),
    "thematic_areas": _("áreas temáticas"),
    "directory": _("Dados"),
    "indicator": _("Indicadores"),
    "practice": _("Práticas"),
    "action": _("Ações"),
    "category": _("Categoria"),
    "geo_scope": _("Escopo geográfico"),
    "thematic_scope": _("Escopo temático"),
    "institutional_contribution": _("Contribuição"),
    "CURRENT": _("Corrente"),
    "OUTDATED": _("Desatualizado"),
    "curso livre": _("curso livre"),
    "disciplina de graduação": _("disciplina de graduação"),
    "disciplina de lato sensu": _("disciplina de lato sensu"),
    "disciplina de stricto sensu": _("disciplina de stricto sensu"),
    "encontro": _("encontro"),
    "conferência": _("conferência"),
    "congresso": _("congresso"),
    "workshop": _("workshop"),
    "seminário": _("seminário"),
    "outros": _("outros"),
    "portal": _("Portal"),
    "plataforma": _("Plataforma"),
    "servidor": _("Servidor"),
    "repositório": _("Repositório"),
    "serviço": _("Serviço"),
    "promoção": _("promoção"),
    "posicionamento": _("posicionamento"),
    "mandato": _("mandato"),
    "geral": _("geral"),
    "outras": _("Outras"),
    "FREQUENCY": _("Frequência"),
    "EVOLUTION": _("Evolução"),
    "AVERAGE": _("Média"),
    "RELATIVE_FREQUENCY": _("Frequência relativa"),
    "GENERAL": _("Geral"),
    "INSTITUTIONAL": _("Instituticional"),
    "GEOGRAPHIC": _("Geográfico"),
    "CHRONOLOGICAL": _("Cronológico"),
    "THEMATIC": _("Temático"),
    "closed": _("Fechado"),
    "gold": _("Ouro"),
    "bronze": _("Bronze"),
    "hybrid": _("Hibrído"),
    "green": _("Verde"),
    "diamond": _("Diamante"),
    "year": _("Ano"),
    "true": _("Sim"),
    "false": _("Não"),
    "article": _("Artigo"),
    "book": _("Livro"),
    "bookchapter": _("Capítulo de livro"),
    "chapter": _("Capítulo"),
    "editorial": _("Editorial"),
    "dissertation": _("Dissertação"),
    "paratext": _("Paratexto"),
    "dataset": _("Conjunto de dados"),
    "erratum": _("Errata"),
    "other": _("Outro"),
    "others": _("Outros"),
    "report": _("Relatório"),
    "entry": _("Verbete"),
    "reference": _("Referência"),
    "referenceentry": _("Entrada de referência"),
    "journal": _("Periódico"),
    "journalarticle": _("Artigo de periódico"),
    "peer": _("Pares"),
    "peerreview": _("Revisão por pares"),
    "review": _("Revisão"),
    "letter": _("Carta"),
    "proceedings": _("Anais"),
    "content": _("Conteúdo"),
    "posted": _("Publicado"),
    "postedcontent": _("Conteúdo publicado"),
    "proceedingsarticle": _("Artigo de anais"),
    "standard": _("Norma"),
    "bookpart": _("Parte de livro"),
    "part": _("Parte"),
    "proceedingsseries": _("Série de anais"),
    "series": _("Série"),
    "year": "ano",
    "thematic_level_0": "Área temática",
    "regions": "Região",
    "open_access_status": "Tipo de acesso aberto",
    "license": "Licença",
    "is_oa": "Acesso aberto (sim/não)",
    "type": "tipo de documento",
    "brazil": "Brasil",
    "world": "Mundo",
    "world_region": "Mundo - região",
    "world_country": "Mundo - país",
    "brazil_region": "Brasil - região",
    "brazil_state": "Brasil - estado",
    "brazil_instituion": "Brasil - instituição",
    "literatura em acesso aberto": "Literatura em acesso aberta",
    "menção genérica à CA ou todas as práticas": "Menção genérica à CA ou todas as práticas",
    "outras práticas": "Outras práticas",
    "recursos educacionais abertos": "Recursos educacionais abertos",
    "dados abertos de pesquisa": "Dados abertos de pesquisa",
    "ciência cidadã": "Ciência cidadã",
    "peer review aberto": "Peer review aberto",
}


country_list = [
    ("United States of America", "US"),
    ("China", "CN"),
    ("United Kingdom of Great Britain and Northern Ireland", "GB"),
    ("Germany", "DE"),
    ("Japan", "JP"),
    ("France", "FR"),
    ("India", "IN"),
    ("Canada", "CA"),
    ("Brazil", "BR"),
    ("Italy", "IT"),
    ("Spain", "ES"),
    ("Australia", "AU"),
    ("Russian Federation", "RU"),
    ("Indonesia", "ID"),
    ("Korea, Republic of", "KR"),
    ("Netherlands", "NL"),
    ("Poland", "PL"),
    ("Switzerland", "CH"),
    ("Turkey", "TR"),
    ("Sweden", "SE"),
    ("Belgium", "BE"),
    ("Iran, Islamic Republic of", "IR"),
    ("Taiwan, Province of China", "TW"),
    ("Mexico", "MX"),
    ("Denmark", "DK"),
    ("Austria", "AT"),
    ("Israel", "IL"),
    ("Portugal", "PT"),
    ("Czechia", "CZ"),
    ("Malaysia", "MY"),
    ("South Africa", "ZA"),
    ("Norway", "NO"),
    ("Finland", "FI"),
    ("Egypt", "EG"),
    ("Greece", "GR"),
    ("Singapore", "SG"),
    ("Argentina", "AR"),
    ("Saudi Arabia", "SA"),
    ("Ukraine", "UA"),
    ("Pakistan", "PK"),
    ("Colombia", "CO"),
    ("New Zealand", "NZ"),
    ("Ireland", "IE"),
    ("Hong Kong", "HK"),
    ("Chile", "CL"),
    ("Hungary", "HU"),
    ("Nigeria", "NG"),
    ("Romania", "RO"),
    ("Thailand", "TH"),
    ("Croatia", "HR"),
    ("Slovakia", "SK"),
    ("Bangladesh", "BD"),
    ("Serbia", "RS"),
    ("Viet Nam", "VN"),
    ("Iraq", "IQ"),
    ("Morocco", "MA"),
    ("Slovenia", "SI"),
    ("Bulgaria", "BG"),
    ("Peru", "PE"),
    ("Algeria", "DZ"),
    ("Tunisia", "TN"),
    ("Panama", "PA"),
    ("United Arab Emirates", "AE"),
    ("Cuba", "CU"),
    ("Ecuador", "EC"),
    ("Philippines", "PH"),
    ("Kenya", "KE"),
    ("Ethiopia", "ET"),
    ("Venezuela, Bolivarian Republic of", "VE"),
    ("Jordan", "JO"),
    ("Lithuania", "LT"),
    ("Ghana", "GH"),
    ("Qatar", "QA"),
    ("Nepal", "NP"),
    ("Estonia", "EE"),
    ("Kazakhstan", "KZ"),
    ("Costa Rica", "CR"),
    ("Belarus", "BY"),
    ("Cyprus", "CY"),
    ("Sri Lanka", "LK"),
    ("Lebanon", "LB"),
    ("Latvia", "LV"),
    ("Uzbekistan", "UZ"),
    ("Luxembourg", "LU"),
    ("Uruguay", "UY"),
    ("Puerto Rico", "PR"),
    ("Tanzania, United Republic of", "TZ"),
    ("Cameroon", "CM"),
    ("Uganda", "UG"),
    ("Kuwait", "KW"),
    ("Macao", "MO"),
    ("Oman", "OM"),
    ("Azerbaijan", "AZ"),
    ("Iceland", "IS"),
    ("Bosnia and Herzegovina", "BA"),
    ("Tajikistan", "TJ"),
    ("Armenia", "AM"),
    ("Georgia", "GE"),
    ("Sudan", "SD"),
    ("Bolivia, Plurinational State of", "BO"),
    ("North Macedonia", "MK"),
    ("Zimbabwe", "ZW"),
    ("Mongolia", "MN"),
    ("Côte d'Ivoire", "CI"),
    ("Senegal", "SN"),
    ("Moldova, Republic of", "MD"),
    ("Yemen", "YE"),
    ("South Sudan", "SS"),
    ("Mozambique", "MZ"),
    ("Cambodia", "KH"),
    ("Palestine, State of", "PS"),
    ("Zambia", "ZM"),
    ("Malta", "MT"),
    ("Paraguay", "PY"),
    ("Benin", "BJ"),
    ("Bahrain", "BH"),
    ("Albania", "AL"),
    ("Guatemala", "GT"),
    ("Burkina Faso", "BF"),
    ("Malawi", "MW"),
    ("Myanmar", "MM"),
    ("Syrian Arab Republic", "SY"),
    ("Botswana", "BW"),
    ("Jamaica", "JM"),
    ("Libya", "LY"),
    ("Mali", "ML"),
    ("Niger", "NE"),
    ("Congo, Democratic Republic of the", "CD"),
    ("Virgin Islands, British", "VG"),
    ("Burundi", "BI"),
    ("Brunei Darussalam", "BN"),
    ("Réunion", "RE"),
    ("Rwanda", "RW"),
    ("Trinidad and Tobago", "TT"),
    ("Montenegro", "ME"),
    ("El Salvador", "SV"),
    ("Kosovo", "XK"),
    ("Kyrgyzstan", "KG"),
    ("Nicaragua", "NI"),
    ("Honduras", "HN"),
    ("Dominican Republic", "DO"),
    ("Madagascar", "MG"),
    ("Fiji", "FJ"),
    ("Namibia", "NA"),
    ("Guadeloupe", "GP"),
    ("Congo", "CG"),
    ("Mauritius", "MU"),
    ("Afghanistan", "AF"),
    ("Papua New Guinea", "PG"),
    ("Togo", "TG"),
    ("Angola", "AO"),
    ("Sao Tome and Principe", "ST"),
    ("Gambia", "GM"),
    ("Gabon", "GA"),
    ("Grenada", "GD"),
    ("Lao People's Democratic Republic", "LA"),
    ("Barbados", "BB"),
    ("Guinea-Bissau", "GW"),
    ("Liechtenstein", "LI"),
    ("Monaco", "MC"),
    ("Sierra Leone", "SL"),
    ("New Caledonia", "NC"),
    ("French Polynesia", "PF"),
    ("Martinique", "MQ"),
    ("French Guiana", "GF"),
    ("Antigua and Barbuda", "AG"),
    ("Greenland", "GL"),
    ("Guinea", "GN"),
    ("Guam", "GU"),
    ("Eswatini", "SZ"),
    ("Bhutan", "BT"),
    ("Saint Kitts and Nevis", "KN"),
    ("Curaçao", "CW"),
    ("Guyana", "GY"),
    ("Bahamas", "BS"),
    ("Lesotho", "LS"),
    ("Maldives", "MV"),
    ("Chad", "TD"),
    ("Turkmenistan", "TM"),
    ("Somalia", "SO"),
    ("Faroe Islands", "FO"),
    ("Liberia", "LR"),
    ("Virgin Islands, U.S.", "VI"),
    ("Bermuda", "BM"),
    ("Haiti", "HT"),
    ("Central African Republic", "CF"),
    ("Mauritania", "MR"),
    ("Cabo Verde", "CV"),
    ("Eritrea", "ER"),
    ("Gibraltar", "GI"),
    ("Suriname", "SR"),
    ("Korea, Democratic People's Republic of", "KP"),
    ("Cayman Islands", "KY"),
    ("Belize", "BZ"),
    ("Seychelles", "SC"),
    ("Timor-Leste", "TL"),
    ("Holy See", "VA"),
    ("Isle of Man", "IM"),
    ("San Marino", "SM"),
    ("Samoa", "WS"),
]

scimago_region = {
    "Western Europe": [
        "AD",
        "AT",
        "BE",
        "BV",
        "CY",
        "DK",
        "FO",
        "FI",
        "FR",
        "DE",
        "GI",
        "GR",
        "GL",
        "GG",
        "VA",
        "IS",
        "IE",
        "IM",
        "IT",
        "JE",
        "LI",
        "LU",
        "MT",
        "MC",
        "NL",
        "NO",
        "PT",
        "SM",
        "ES",
        "SJ",
        "SE",
        "CH",
        "GB",
        "AX",
    ],
    "Pacific Region": [
        "AS",
        "AU",
        "CX",
        "CC",
        "CK",
        "FJ",
        "PF",
        "TF",
        "GU",
        "HM",
        "KI",
        "MH",
        "FM",
        "NR",
        "NC",
        "NZ",
        "NU",
        "NF",
        "PW",
        "PG",
        "PN",
        "WS",
        "SB",
        "TK",
        "TO",
        "TV",
        "VU",
        "WF",
    ],
    "Northern America": ["CA", "PM", "UM", "US"],
    "Middle East": [
        "BH",
        "IR",
        "IQ",
        "IL",
        "JO",
        "KW",
        "LB",
        "OM",
        "PS",
        "QA",
        "SA",
        "SY",
        "TR",
        "AE",
        "YE",
    ],
    "Latin America": [
        "AI",
        "AG",
        "AR",
        "AW",
        "BS",
        "BB",
        "BZ",
        "BM",
        "BO",
        "BQ",
        "BR",
        "KY",
        "CL",
        "CO",
        "CR",
        "CU",
        "CW",
        "DM",
        "DO",
        "EC",
        "SV",
        "FK",
        "GF",
        "GD",
        "GP",
        "GT",
        "GY",
        "HT",
        "HN",
        "JM",
        "MQ",
        "MX",
        "MS",
        "NI",
        "PA",
        "PY",
        "PE",
        "PR",
        "BL",
        "KN",
        "LC",
        "MF",
        "VC",
        "SX",
        "GS",
        "SR",
        "TT",
        "TC",
        "UY",
        "VE",
        "VG",
        "VI",
    ],
    "Eastern Europe": [
        "AL",
        "AM",
        "AZ",
        "BY",
        "BA",
        "BG",
        "HR",
        "CZ",
        "EE",
        "GE",
        "HU",
        "LV",
        "LT",
        "MD",
        "ME",
        "MK",
        "PL",
        "RO",
        "RU",
        "RS",
        "SK",
        "SI",
        "UA",
        "XK",
    ],
    "Asiatic Region": [
        "AF",
        "BD",
        "BT",
        "BN",
        "KH",
        "CN",
        "HK",
        "IN",
        "ID",
        "JP",
        "KZ",
        "KP",
        "KR",
        "KG",
        "LA",
        "MO",
        "MY",
        "MV",
        "MN",
        "MM",
        "NP",
        "MP",
        "PK",
        "PH",
        "SG",
        "LK",
        "TW",
        "TJ",
        "TH",
        "TL",
        "TM",
        "UZ",
        "VN",
    ],
    "Antarctica": ["QA"],
    "Africa": [
        "DZ",
        "AO",
        "BJ",
        "BW",
        "IO",
        "BF",
        "BI",
        "CV",
        "CM",
        "CF",
        "TD",
        "KM",
        "CG",
        "CD",
        "CI",
        "DJ",
        "EG",
        "GQ",
        "ER",
        "SZ",
        "ET",
        "GA",
        "GM",
        "GH",
        "GN",
        "GW",
        "KE",
        "LS",
        "LR",
        "LY",
        "MG",
        "MW",
        "ML",
        "MR",
        "MU",
        "YT",
        "MA",
        "MZ",
        "NA",
        "NE",
        "NG",
        "RW",
        "RE",
        "SH",
        "ST",
        "SN",
        "SC",
        "SL",
        "SO",
        "ZA",
        "SS",
        "SD",
        "TZ",
        "TG",
        "TN",
        "UG",
        "EH",
        "ZM",
        "ZW",
    ],
}

