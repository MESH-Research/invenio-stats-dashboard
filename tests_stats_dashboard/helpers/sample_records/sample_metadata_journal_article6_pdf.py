# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Sample metadata for a journal article 6 with PDF file for testing purposes."""

sample_metadata_journal_article6_pdf = {
    "id": "5ryf5-bfn20",
    "created": "2025-05-30T23:53:04.686003+00:00",
    "metadata": {
        "resource_type": {
            "id": "textDocument-journalArticle",
            "title": {"de": "Zeitschriftenartikel", "en": "Journal article"},
        },
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Austin, Jeanie",
                    "given_name": "Jeanie",
                    "family_name": "Austin",
                    "identifiers": [
                        {"identifier": "0009-0008-0969-5474", "scheme": "orcid"},
                    ],
                },
                "role": {"id": "author", "title": {"en": "Author"}},
                "affiliations": [{"name": "San Francisco Public Library"}],
            },
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Ness, Nili",
                    "given_name": "Nili",
                    "family_name": "Ness",
                },
                "role": {"id": "author", "title": {"en": "Author"}},
                "affiliations": [{"name": "San Francisco Public Library"}],
            },
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Okelo, Bee",
                    "given_name": "Bee",
                    "family_name": "Okelo",
                },
                "role": {"id": "author", "title": {"en": "Author"}},
                "affiliations": [
                    {"id": "013v4ng57", "name": "San Francisco Public Library"}
                ],
            },
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Kinnon, Rachel",
                    "given_name": "Rachel",
                    "family_name": "Kinnon",
                },
                "role": {"id": "author", "title": {"en": "Author"}},
                "affiliations": [{"name": "San Francisco Public Library"}],
            },
        ],
        "title": (
            "Trends and Concerns in Library Services for Incarcerated People and People in the Process of Reentry: Publication Review (2020-2022)"  # noqa: E501
        ),
        "publisher": "Knowledge Commons",
        "publication_date": "2023-11-01",
        "subjects": [
            {
                "id": "http://id.worldcat.org/fast/997916",
                "subject": "Library science",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/2060143",
                "subject": "Mass incarceration",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/997987",
                "subject": "Library science literature",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/997974",
                "subject": "Library science--Standards",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/855500",
                "subject": "Children of prisoners--Services for",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/995415",
                "subject": "Legal assistance to prisoners--U.S. states",
                "scheme": "FAST-topical",
            },
        ],
        "languages": [{"id": "eng", "title": {"en": "English"}}],
        "description": (
            "This is a white paper reviewing publications from 2020-2022 that relate to library and information services for people who are incarcerated or in the process of reentry. It covers a variety of library types, forms of outreach, services to specific demographics, and emerging research concerns."  # noqa: E501
        ),
    },
    "custom_fields": {},
    "access": {
        "record": "public",
        "files": "public",
        "embargo": {"active": False, "reason": None},
        "status": "open",
    },
    "files": {
        "enabled": True,
        "order": [],
        "count": 1,
        "total_bytes": 458036,
        "entries": {
            "Trends and Concerns in Library Services for Incarcerated People and People in the Process of Reentry Publication Review (2020-2022)-1.pdf": {  # noqa: E501
                "ext": "pdf",
                "size": 458036,
                "mimetype": "application/pdf",
                "key": (
                    "Trends and Concerns in Library Services for Incarcerated People and People in the Process of Reentry Publication Review (2020-2022)-1.pdf"  # noqa: E501
                ),
            },
        },
    },
}
