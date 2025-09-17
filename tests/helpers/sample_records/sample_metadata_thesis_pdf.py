# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Sample metadata for a thesis with PDF file for testing purposes."""

sample_metadata_thesis_pdf = {
    "created": "2021-04-26T05:57:56Z",
    "custom_fields": {
        "imprint:imprint": {
            "title": (
                "https://tesiunam.dgb.unam.mx/F/"
                "KVS7IYBX26S3PMEDX1SXFF6XRKP48FV5JRD21J7UNV85V8U82E-42627"
                "?func=full-set-set&set_number=198105&"
                "set_entry=000001&format=999"
            )
        },
        "thesis:university": "Universidad Nacional Autónoma de México (UNAM)",
    },
    "files": {
        "enabled": True,
        "entries": {
            "system-dynamics-growth-distribution-and-financialization.pdf": {  # noqa: E501
                "key": (
                    "system-dynamics-growth-distribution-and-financ" "ialization.pdf"
                ),
                "mimetype": "application/pdf",
                "size": "17181",
            }
        },
    },
    "metadata": {
        "additional_descriptions": [
            {
                "description": (
                    "These models are a representation of "
                    "the macroeconomic evolution of the "
                    "US economy from 1970 to 2010. The main variables "
                    "addressed are economic growth, income "
                    "distribution and private debt. The "
                    "theoretical basis of the model "
                    "relies on what Bhaduri labeled as "
                    'the "Marx-Keynes-Kalecki" '
                    "tradition that has four distinctive "
                    "assumptions: 1) The price of this "
                    "one-commidty model is determined by a "
                    "mark-up over the production costs. "
                    "2) Aggregate demand determines "
                    "(AD) the level of production (Y). 3) "
                    "Investment (I) is the key variable "
                    "within aggregate demand. 4) The "
                    "level of aggregate supply (Yt) is "
                    "equal to aggregate demand (ADt). "
                    "There are other features of the "
                    "model that are also worth to "
                    "pinpoint. The baseline model has "
                    "three sectors: workers, "
                    "industrial capital and private "
                    "banking. The first two sectors are "
                    "clearly differentiated by "
                    "the marginal propensities of "
                    "their members to consume and their "
                    "access to credit. Workers have a "
                    "marginal propensity to "
                    "consume that goes from 0.5 to 1.3. "
                    "The propensity of consumption of "
                    "this sector varies with respect to "
                    'two macro-level "shaping '
                    'structures" that determine this '
                    "sector's microeconomic "
                    "behavior. Workers' propensity to "
                    "consume varies non-linearly "
                    "regarding inflation, and it "
                    "exhibits a positive and "
                    "linear relationship with "
                    "respect to the industrial "
                    "capital's share on total income. On "
                    "the other hand, capitalists can "
                    "save or become indebted depending "
                    "on the saving-investment gap. Any investment "
                    "decision over savings is always financed by the "
                    "acquisition of private debt "
                    "provided by private banks, and "
                    "the excess of savings is used to "
                    "pay the debt contracted by the "
                    "capitalists. Whilst the "
                    "activity of private banking is "
                    "limited only to the granting of "
                    "credit, the accumulation of "
                    "private debt represents its "
                    "source of profits. A subsidiary "
                    "assumption that is maintained "
                    "throughout this model is that it "
                    "is a closed economy without "
                    "government."
                ),
                "type": {"id": "other", "title": {"en": "Other"}},
            }
        ],
        "creators": [
            {
                "affiliations": [{"name": "Université Sorbonne Paris Nord"}],
                "person_or_org": {
                    "family_name": "Martínez Hernández",
                    "given_name": "Alberto-Gabino",
                    "name": "Martínez Hernández, Alberto-Gabino",
                    "type": "personal",
                },
                "role": {"id": "author", "title": {"en": "Author"}},
            }
        ],
        "description": (
            "These models are a representation of the "
            "macroeconomic evolution of the US economy from "
            "1970 to 2010. The main variables addressed are "
            "economic growth, income distribution and "
            "private debt. The theoretical basis of the "
            "model relies on what Bhaduri labeled as the "
            '"Marx-Keynes-Kalecki" tradition that has four '
            "distinctive assumptions: \n"
            "\n"
            "1) The price of this one-commidty model is "
            "determined by a mark-up over the production "
            "costs. \n"
            "2) Aggregate demand determines (AD) the level "
            "of production (Y).\n"
            "3) Investment (I) is the key variable within "
            "aggregate demand. \n"
            "4) The level of aggregate supply (Yt) is equal "
            "to aggregate demand (ADt). \n"
            "\n"
            "There are other features of the model that are "
            "also worth to pinpoint. The baseline model has "
            "three sectors: workers, industrial capital and "
            "private banking. The first two sectors are "
            "clearly differentiated by the marginal "
            "propensities of their members to consume and "
            "their access to credit. Workers have a marginal "
            "propensity to consume that goes from 0.5 to "
            "1.3. The propensity of consumption of this "
            "sector varies with respect to two macro-level "
            '"shaping structures" that determine this '
            "sector's microeconomic behavior. Workers' "
            "propensity to consume varies non-linearly "
            "regarding inflation, and it exhibits a positive "
            "and linear relationship with respect to the "
            "industrial capital's share on total income. On "
            "the other hand, capitalists can save or become "
            "indebted depending on the saving-investment "
            "gap. Any investment decision over savings is "
            "always financed by the acquisition of private "
            "debt provided by private banks, and the excess "
            "of savings is used to pay the debt contracted "
            "by the capitalists. Whilst the activity of "
            "private banking is limited only to the granting "
            "of credit, the accumulation of private debt "
            "represents its source of profits. A subsidiary "
            "assumption that is maintained throughout this "
            "model is that it is a closed economy without "
            "government."
        ),
        "identifiers": [
            {
                "identifier": "http://132.248.9.195/ptd2018/mayo/0774053/Index.html",
                "scheme": "url",
            },
        ],
        "languages": [{"id": "spa", "title": {"en": "Spanish"}}],
        "publication_date": "2018",
        "resource_type": {"id": "textDocument-thesis"},
        "rights": [
            {
                "description": {
                    "en": (
                        "Proprietary material. No permissions are "
                        "granted for any kind of copyring or "
                        "re-use. All rights reserved"
                    )
                },
                "id": "arr",
                "icon": "copyright",
                "props": {"url": "https://en.wikipedia.org/wiki/All_rights_reserved"},
                "title": {"en": "All Rights Reserved"},
            }
        ],
        "subjects": [
            {
                "id": "http://id.worldcat.org/fast/902116",
                "subject": "Economics",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/958235",
                "subject": "History",
                "scheme": "FAST-topical",
            },
            {
                "id": "http://id.worldcat.org/fast/1012163",
                "subject": "Mathematics",
                "scheme": "FAST-topical",
            },
        ],
        "publisher": "Universidad Nacional Autónoma de Mexico (UNAM)",
        "title": (
            "The macroeconomic evolution of the USA, 1970 - 2010. "
            "A heterodox mathematical modelling approach with "
            "System Dynamics."
        ),
    },
}
