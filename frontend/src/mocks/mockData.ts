// Authoritative Mock Data for EvidenceFlow (Mini-Rayyan Hackathon)
// Generated strictly according to API_CONTRACTS.md and section 5 schema

import {
  Review,
  CriteriaVersion,
  QueryVersion,
  LiteratureRecord,
  DuplicatePair,
  PairDecision,
  PicoAnnotation,
  Conflict,
  PipelineRun,
  DiffSummary,
  AuditEvent
} from '../types/api';

export const mockReview: Review = {
  "id": 1,
  "title": "Metformin vs Placebo in Type 2 Diabetes",
  "question": "In adults with type 2 diabetes, does metformin, compared with placebo, lower HbA1c?",
  "population": "Adults with type 2 diabetes",
  "intervention": "Metformin",
  "comparator": "Placebo or standard care",
  "outcome": "Change in HbA1c (glycated haemoglobin)",
  "active_criteria_version_id": 1,
  "created_at": "2026-10-24T18:00:00Z",
  "updated_at": "2026-10-24T18:00:00Z",
  "stats": {
    "total_records": 11,
    "unique_groups": 8,
    "included": 2,
    "excluded": 4,
    "maybe": 1,
    "unscreened": 4,
    "conflicts": 1,
    "uncertain_duplicates": 1
  }
};

export const mockCriteriaVersion: CriteriaVersion = {
  "id": 1,
  "review_id": 1,
  "version_no": 1,
  "created_at": "2026-10-24T18:05:00Z",
  "created_by": "Member A",
  "criteria": [
    {
      "id": 1,
      "criteria_version_id": 1,
      "kind": "exclude",
      "code": "non_human",
      "label": "Non-Human Studies",
      "reason": "The review question focuses specifically on human adult patients with type 2 diabetes.",
      "detector": "metadata_then_rule",
      "params_json": {
        "mesh_terms": [
          "Animals",
          "Rats",
          "Mice"
        ],
        "species_regex": [
          "rat",
          "mouse",
          "murine",
          "porcine",
          "in vitro"
        ]
      },
      "is_active": true
    },
    {
      "id": 2,
      "criteria_version_id": 1,
      "kind": "exclude",
      "code": "non_english",
      "label": "Non-English Publications",
      "reason": "Reviewing team lacks verified multilingual translation capabilities for non-English literature.",
      "detector": "metadata_then_rule",
      "params_json": {
        "allowed_languages": [
          "eng",
          "en"
        ]
      },
      "is_active": true
    },
    {
      "id": 3,
      "criteria_version_id": 1,
      "kind": "exclude",
      "code": "case_report",
      "label": "Case Reports & Series",
      "reason": "Isolated case reports cannot establish statistical average treatment effects.",
      "detector": "metadata_then_rule",
      "params_json": {
        "pub_types": [
          "Case Reports"
        ],
        "regex": [
          "case report",
          "we report a case",
          "single patient"
        ]
      },
      "is_active": true
    },
    {
      "id": 4,
      "criteria_version_id": 1,
      "kind": "exclude",
      "code": "simulation",
      "label": "In Silico / Simulation Studies",
      "reason": "Mathematical simulation models do not measure biological responses in live human subjects.",
      "detector": "rule",
      "params_json": {
        "terms": [
          "simulation",
          "in silico",
          "Markov model",
          "Monte Carlo",
          "microsimulation"
        ]
      },
      "is_active": true
    },
    {
      "id": 5,
      "criteria_version_id": 1,
      "kind": "include",
      "code": "adult_population",
      "label": "Adult Type 2 Diabetes",
      "reason": "Study must involve adults (>=18 yrs) diagnosed with type 2 diabetes mellitus.",
      "detector": "rule",
      "params_json": {
        "terms": [
          "type 2 diabetes",
          "T2D",
          "adults",
          "patients"
        ]
      },
      "is_active": true
    },
    {
      "id": 6,
      "criteria_version_id": 1,
      "kind": "include",
      "code": "metformin_comparator",
      "label": "Metformin vs Comparator",
      "reason": "Study evaluates metformin against placebo, diet, or active comparator.",
      "detector": "rule",
      "params_json": {
        "terms": [
          "metformin",
          "placebo",
          "control",
          "glipizide"
        ]
      },
      "is_active": true
    }
  ]
};

export const mockQueryVersions: QueryVersion[] = [
  {
    "id": 1,
    "review_id": 1,
    "lineage_root_id": 1,
    "parent_id": null,
    "version_no": 1,
    "label": "Initial Specific Search (Metformin AND Placebo)",
    "source": "europe_pmc",
    "expression": "(\"type 2 diabetes\" OR \"type II diabetes\") AND metformin AND placebo",
    "date_from": "2015-01-01",
    "date_to": "2025-12-31",
    "options_json": {
      "synonym": false
    },
    "import_cap": 500,
    "status": "imported",
    "hit_count": 1842,
    "imported_count": 500,
    "created_at": "2026-10-24T18:15:00Z",
    "executed_at": "2026-10-24T18:16:30Z",
    "request_fingerprint": "fp-v1-metformin-placebo"
  },
  {
    "id": 2,
    "review_id": 1,
    "lineage_root_id": 1,
    "parent_id": 1,
    "version_no": 2,
    "label": "Expanded Search (Broadened Comparator Scope)",
    "source": "europe_pmc",
    "expression": "(\"type 2 diabetes\" OR \"type II diabetes\") AND metformin",
    "date_from": "2015-01-01",
    "date_to": "2025-12-31",
    "options_json": {
      "synonym": false
    },
    "import_cap": 500,
    "status": "imported",
    "hit_count": 3410,
    "imported_count": 500,
    "created_at": "2026-10-25T09:00:00Z",
    "executed_at": "2026-10-25T09:02:10Z",
    "request_fingerprint": "fp-v2-metformin-broad"
  }
];

export const mockRecords: LiteratureRecord[] = [
  {
    "id": 101,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "PMC7482910",
    "doi_norm": "10.1136/bmj.m2810",
    "pmid": "32928765",
    "pmcid": "PMC7482910",
    "title": "Metformin versus Placebo in Patients with Type 2 Diabetes: A 10-Year Follow-up of Glycemic Control and Microvascular Complications",
    "title_norm": "metformin versus placebo in patients with type 2 diabetes a 10-year follow-up of glycemic control and microvascular complications",
    "abstract": "Adults with type 2 diabetes (n=1200) received metformin 1000mg twice daily or placebo for 10 years; the primary outcome was change in HbA1c and incidence of microvascular complications. Metformin significantly lowered mean HbA1c compared to placebo.",
    "authors_json": [
      "Holman R.R.",
      "Matthews D.R.",
      "Turner R.C."
    ],
    "first_author_norm": "holman",
    "year": 2020,
    "journal": "British Medical Journal",
    "journal_norm": "british medical journal",
    "volume": "370",
    "issue": "8261",
    "pages": "m2810",
    "language": "eng",
    "pub_types_json": [
      "Randomized Controlled Trial",
      "Journal Article"
    ],
    "mesh_json": [
      "Metformin",
      "Diabetes Mellitus, Type 2",
      "Glycated Hemoglobin",
      "Humans",
      "Adult"
    ],
    "content_hash": "a1b2c3d4e5f6001",
    "created_at": "2026-10-24T18:16:35Z",
    "updated_at": "2026-10-24T18:16:35Z",
    "is_representative": true,
    "group_id": "group-101",
    "group_members_count": 2,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 501,
      "record_id": 101,
      "criteria_version_id": 1,
      "content_hash": "a1b2c3d4e5f6001",
      "algo_version": "v1.0",
      "suggestion": "include",
      "criterion_id": null,
      "evidence_json": {
        "strength": "strong",
        "explanation": "Human trial matching adult type 2 diabetes population and metformin vs placebo comparator.",
        "matched_criteria": [
          5,
          6
        ],
        "metadata_fields_used": [
          "mesh",
          "pub_types"
        ]
      },
      "created_at": "2026-10-24T18:16:40Z"
    },
    "current_decision": {
      "id": 601,
      "review_id": 1,
      "record_id": 101,
      "decision": "include",
      "reason_text": "High quality randomized controlled trial directly addressing review question",
      "reviewer": "Member D",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:30:00Z"
    }
  },
  {
    "id": 102,
    "review_id": 1,
    "source": "pubmed",
    "source_record_id": "32928765",
    "doi_norm": "10.1136/bmj.m2810",
    "pmid": "32928765",
    "title": "Metformin versus Placebo in Patients with Type 2 Diabetes: A 10-Year Follow-up of Glycemic Control and Microvascular Complications",
    "title_norm": "metformin versus placebo in patients with type 2 diabetes a 10-year follow-up of glycemic control and microvascular complications",
    "abstract": "Adults with type 2 diabetes (n=1200) received metformin 1000mg twice daily or placebo for 10 years; the primary outcome was change in HbA1c and incidence of microvascular complications. Metformin significantly lowered mean HbA1c compared to placebo.",
    "authors_json": [
      "Holman RR",
      "Matthews DR",
      "Turner RC"
    ],
    "first_author_norm": "holman",
    "year": 2020,
    "journal": "BMJ",
    "journal_norm": "bmj",
    "language": "eng",
    "pub_types_json": [
      "Randomized Controlled Trial",
      "Journal Article"
    ],
    "mesh_json": [
      "Metformin",
      "Diabetes Mellitus, Type 2",
      "Humans"
    ],
    "content_hash": "a1b2c3d4e5f6002",
    "created_at": "2026-10-24T18:16:36Z",
    "updated_at": "2026-10-24T18:16:36Z",
    "is_representative": false,
    "group_id": "group-101",
    "group_members_count": 2,
    "query_versions": [
      1
    ],
    "current_decision": {
      "id": 602,
      "review_id": 1,
      "record_id": 102,
      "decision": "include",
      "reason_text": "Inherited from representative record #101",
      "reviewer": "Member D",
      "origin": "inherited",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:30:00Z"
    }
  },
  {
    "id": 103,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "28372091",
    "doi_norm": "10.2337/dc16-2412",
    "pmid": "28372091",
    "title": "Efficacy of Metformin Monotherapy in Newly Diagnosed Type 2 Diabetes: A Multicenter Randomized Double-Blind Trial",
    "title_norm": "efficacy of metformin monotherapy in newly diagnosed type 2 diabetes a multicenter randomized double-blind trial",
    "abstract": "Patients with type 2 diabetes were randomized to metformin 850mg or active comparator for 24 weeks. Glycated hemoglobin (HbA1c) dropped by 1.2% in the metformin arm vs 0.8% with comparator.",
    "authors_json": [
      "Kahn S.E.",
      "Haffner S.M.",
      "Heise M.A."
    ],
    "first_author_norm": "kahn",
    "year": 2017,
    "journal": "Diabetes Care",
    "journal_norm": "diabetes care",
    "volume": "40",
    "issue": "6",
    "pages": "790-798",
    "language": "eng",
    "pub_types_json": [
      "Randomized Controlled Trial",
      "Journal Article"
    ],
    "mesh_json": [
      "Metformin",
      "Diabetes Mellitus, Type 2",
      "Humans",
      "Adult"
    ],
    "content_hash": "kahn2017dc",
    "created_at": "2026-10-24T18:16:42Z",
    "updated_at": "2026-10-24T18:16:42Z",
    "is_representative": true,
    "group_id": "group-103",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 502,
      "record_id": 103,
      "criteria_version_id": 1,
      "content_hash": "kahn2017dc",
      "algo_version": "v1.0",
      "suggestion": "include",
      "criterion_id": null,
      "evidence_json": {
        "strength": "strong",
        "explanation": "Human RCT comparing metformin with active comparator in adult T2D patients.",
        "matched_criteria": [
          5,
          6
        ]
      },
      "created_at": "2026-10-24T18:16:45Z"
    }
  },
  {
    "id": 104,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "CONF-ADA-2016-104",
    "title": "Efficacy of Metformin Monotherapy in Newly Diagnosed Type 2 Diabetes: Preliminary Results of a Multicenter Double-Blind Trial",
    "title_norm": "efficacy of metformin monotherapy in newly diagnosed type 2 diabetes preliminary results of a multicenter double-blind trial",
    "abstract": "Preliminary conference abstract on 350 patients randomized to metformin vs active comparator.",
    "authors_json": [
      "Kahn S.E.",
      "Haffner S.M."
    ],
    "first_author_norm": "kahn",
    "year": 2016,
    "journal": "Diabetes",
    "journal_norm": "diabetes",
    "language": "eng",
    "pub_types_json": [
      "Meeting Abstract"
    ],
    "mesh_json": [
      "Metformin",
      "Diabetes Mellitus, Type 2"
    ],
    "content_hash": "kahn2016abstract",
    "created_at": "2026-10-24T18:16:44Z",
    "updated_at": "2026-10-24T18:16:44Z",
    "is_representative": true,
    "group_id": "group-104",
    "group_members_count": 1,
    "query_versions": [
      1
    ]
  },
  {
    "id": 105,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "29104821",
    "doi_norm": "10.1016/j.ejphar.2017.11.002",
    "pmid": "29104821",
    "title": "Metformin Alleviates Hepatic Steatosis and Insulin Resistance in Sprague-Dawley Rats Fed a High-Fat Diet",
    "title_norm": "metformin alleviates hepatic steatosis and insulin resistance in sprague-dawley rats fed a high-fat diet",
    "abstract": "Male Sprague-Dawley rats were divided into control and high-fat diet groups. Metformin was administered at 200 mg/kg daily. Hepatic tissue was harvested for Western blot and histological evaluation.",
    "authors_json": [
      "Zhang Y.",
      "Liu W.",
      "Chen X."
    ],
    "first_author_norm": "zhang",
    "year": 2018,
    "journal": "European Journal of Pharmacology",
    "journal_norm": "european journal of pharmacology",
    "volume": "818",
    "pages": "342-350",
    "language": "eng",
    "pub_types_json": [
      "Journal Article"
    ],
    "mesh_json": [
      "Animals",
      "Rats",
      "Rats, Sprague-Dawley",
      "Metformin",
      "Insulin Resistance"
    ],
    "content_hash": "zhangrat2018",
    "created_at": "2026-10-24T18:16:48Z",
    "updated_at": "2026-10-24T18:16:48Z",
    "is_representative": true,
    "group_id": "group-105",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 503,
      "record_id": 105,
      "criteria_version_id": 1,
      "content_hash": "zhangrat2018",
      "algo_version": "v1.0",
      "suggestion": "exclude",
      "criterion_id": 1,
      "evidence_json": {
        "strength": "strong",
        "explanation": "Non-human animal study identified via MeSH descriptor 'Animals' and 'Rats, Sprague-Dawley'.",
        "mesh_hits": [
          "Animals",
          "Rats, Sprague-Dawley"
        ],
        "regex_hits": [
          "sprague-dawley rats",
          "male sprague-dawley"
        ]
      },
      "created_at": "2026-10-24T18:16:50Z"
    },
    "current_decision": {
      "id": 605,
      "review_id": 1,
      "record_id": 105,
      "decision": "exclude",
      "criterion_id": 1,
      "reason_text": "Non-human animal study (Sprague-Dawley rats)",
      "reviewer": "Member B",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:35:00Z"
    }
  },
  {
    "id": 106,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "27011928",
    "doi_norm": "10.1055/s-0042-101412",
    "pmid": "27011928",
    "title": "Therapie des Typ-2-Diabetes mit Metformin in der haus?rztlichen Praxis: Eine prospektive Beobachtungsstudie",
    "title_norm": "therapie des typ-2-diabetes mit metformin in der hausarztlichen praxis eine prospektive beobachtungsstudie",
    "abstract": "In einer multizentrischen Beobachtungsstudie bei 420 Patienten mit Typ-2-Diabetes wurde die Wirksamkeit und Vertr?glichkeit von Metformin ?ber 12 Monate untersucht. HbA1c sank signifikant.",
    "authors_json": [
      "M?ller H.",
      "Schmidt K.",
      "Schneider W."
    ],
    "first_author_norm": "muller",
    "year": 2016,
    "journal": "Deutsche Medizinische Wochenschrift",
    "language": "ger",
    "pub_types_json": [
      "Journal Article"
    ],
    "mesh_json": [
      "Metformin",
      "Diabetes Mellitus, Type 2",
      "Humans"
    ],
    "content_hash": "mullergerman2016",
    "created_at": "2026-10-24T18:16:52Z",
    "updated_at": "2026-10-24T18:16:52Z",
    "is_representative": true,
    "group_id": "group-106",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 504,
      "record_id": 106,
      "criteria_version_id": 1,
      "content_hash": "mullergerman2016",
      "algo_version": "v1.0",
      "suggestion": "exclude",
      "criterion_id": 2,
      "evidence_json": {
        "strength": "strong",
        "explanation": "Language metadata field is 'ger' (German); non-English.",
        "language_field": "ger"
      },
      "created_at": "2026-10-24T18:16:55Z"
    },
    "current_decision": {
      "id": 606,
      "review_id": 1,
      "record_id": 106,
      "decision": "exclude",
      "criterion_id": 2,
      "reason_text": "German publication; team lacks German language proficiency",
      "reviewer": "Member B",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:40:00Z"
    }
  },
  {
    "id": 107,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "31458921",
    "doi_norm": "10.12659/amjcaserep.917821",
    "pmid": "31458921",
    "title": "Severe Lactic Acidosis Induced by Metformin Overdose in a 58-Year-Old Female with Type 2 Diabetes: A Case Report",
    "title_norm": "severe lactic acidosis induced by metformin overdose in a 58-year-old female with type 2 diabetes a case report",
    "abstract": "We report a case of severe metformin-associated lactic acidosis (MALA) in a 58-year-old female presenting with profound shock and metabolic acidosis after accidental overdose.",
    "authors_json": [
      "Lee J.",
      "Park S.",
      "Kim Y."
    ],
    "first_author_norm": "lee",
    "year": 2019,
    "journal": "American Journal of Case Reports",
    "journal_norm": "american journal of case reports",
    "volume": "20",
    "pages": "1245-1249",
    "language": "eng",
    "pub_types_json": [
      "Case Reports"
    ],
    "mesh_json": [
      "Metformin",
      "Acidosis, Lactic",
      "Humans",
      "Female"
    ],
    "content_hash": "leecase2019",
    "created_at": "2026-10-24T18:16:58Z",
    "updated_at": "2026-10-24T18:16:58Z",
    "is_representative": true,
    "group_id": "group-107",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 505,
      "record_id": 107,
      "criteria_version_id": 1,
      "content_hash": "leecase2019",
      "algo_version": "v1.0",
      "suggestion": "exclude",
      "criterion_id": 3,
      "evidence_json": {
        "strength": "strong",
        "explanation": "Publication type is 'Case Reports'; describes individual patient.",
        "pub_type_hits": [
          "Case Reports"
        ],
        "regex_hits": [
          "we report a case",
          "a 58-year-old"
        ]
      },
      "created_at": "2026-10-24T18:17:00Z"
    },
    "current_decision": {
      "id": 607,
      "review_id": 1,
      "record_id": 107,
      "decision": "exclude",
      "criterion_id": 3,
      "reason_text": "Single patient case report; cannot demonstrate average treatment effect",
      "reviewer": "Member B",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:45:00Z"
    }
  },
  {
    "id": 108,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "30109389",
    "doi_norm": "10.2196/12034",
    "pmid": "30109389",
    "title": "Projecting the 20-Year Cost-Effectiveness of Early Metformin: A Markov Microsimulation Model",
    "title_norm": "projecting the twenty-year cost-effectiveness of early metformin a markov microsimulation model",
    "abstract": "A discrete-event microsimulation Markov model was built using NHANES data to project cardiovascular events over 20 years. No direct patient trial measurements.",
    "authors_json": [
      "Johnson K.",
      "Williams P."
    ],
    "first_author_norm": "johnson",
    "year": 2019,
    "journal": "Medical Decision Making",
    "journal_norm": "medical decision making",
    "language": "eng",
    "pub_types_json": [
      "Journal Article"
    ],
    "mesh_json": [
      "Markov Chains",
      "Models, Statistical"
    ],
    "content_hash": "simulationmarkov",
    "created_at": "2026-10-24T18:17:05Z",
    "updated_at": "2026-10-24T18:17:05Z",
    "is_representative": true,
    "group_id": "group-108",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 506,
      "record_id": 108,
      "criteria_version_id": 1,
      "content_hash": "simulationmarkov",
      "algo_version": "v1.0",
      "suggestion": "exclude",
      "criterion_id": 4,
      "evidence_json": {
        "strength": "weak",
        "explanation": "Rule detected computational simulation cues",
        "rule_hits": [
          "microsimulation",
          "Markov model"
        ]
      },
      "created_at": "2026-10-24T18:17:10Z"
    },
    "current_decision": {
      "id": 608,
      "review_id": 1,
      "record_id": 108,
      "decision": "exclude",
      "criterion_id": 4,
      "reason_text": "Computational Markov simulation without direct patient clinical measurements",
      "reviewer": "Member C",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:50:00Z"
    }
  },
  {
    "id": 109,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "31600918",
    "doi_norm": "10.2196/pediatrics.2019-19",
    "pmid": "31600918",
    "title": "Metformin Therapy in Adolescents with Early-Onset Type 2 Diabetes: A Feasibility Pilot Trial",
    "title_norm": "metformin therapy in adolescents with early-onset type 2 diabetes a feasibility pilot trial",
    "abstract": "Pilot study evaluating metformin in 35 adolescents aged 12-17 years with confirmed risk factors. HbA1c decreased by 0.7%. Adult eligibility was not assessed.",
    "authors_json": [
      "Brown A.",
      "Evans T."
    ],
    "first_author_norm": "brown",
    "year": 2021,
    "journal": "Pediatric Diabetes",
    "journal_norm": "pediatric diabetes",
    "language": "eng",
    "pub_types_json": [
      "Journal Article"
    ],
    "mesh_json": [
      "Adolescent",
      "Metformin"
    ],
    "content_hash": "pediatricadolescent",
    "created_at": "2026-10-24T18:17:15Z",
    "updated_at": "2026-10-24T18:17:15Z",
    "is_representative": true,
    "group_id": "group-109",
    "group_members_count": 1,
    "query_versions": [
      1,
      2
    ],
    "suggestion": {
      "id": 507,
      "record_id": 109,
      "criteria_version_id": 1,
      "content_hash": "pediatricadolescent",
      "algo_version": "v1.0",
      "suggestion": "maybe",
      "criterion_id": null,
      "evidence_json": {
        "strength": "weak",
        "explanation": "Population is adolescents (12-17 years); unclear if meeting adult criterion",
        "rule_hits": [
          "adolescents aged 12-17 years"
        ]
      },
      "created_at": "2026-10-24T18:17:18Z"
    },
    "current_decision": {
      "id": 609,
      "review_id": 1,
      "record_id": 109,
      "decision": "maybe",
      "reason_text": "Adolescent pilot; pending consultation with lead reviewer regarding age cutoff",
      "reviewer": "Member D",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:55:00Z"
    }
  },
  {
    "id": 110,
    "review_id": 1,
    "source": "europe_pmc",
    "source_record_id": "35029998",
    "doi_norm": "10.1001/jamadiabetes.2022.04",
    "pmid": "35029998",
    "title": "Metformin Combined with Lifestyle Intervention vs Lifestyle Alone in Impaired Glucose Tolerance (Cohort A)",
    "title_norm": "metformin combined with lifestyle intervention vs lifestyle alone in impaired glucose tolerance",
    "abstract": "Randomized evaluation of metformin 500 mg plus dietary modification in 320 patients with impaired fasting glucose and early T2 diabetes.",
    "authors_json": [
      "Sharma R.",
      "Martinez L."
    ],
    "first_author_norm": "sharma",
    "year": 2022,
    "journal": "Lancet Diabetes & Endocrinology",
    "journal_norm": "lancet diabetes & endocrinology",
    "language": "eng",
    "pub_types_json": [
      "Randomized Controlled Trial"
    ],
    "mesh_json": [
      "Metformin",
      "Glucose Intolerance",
      "Humans"
    ],
    "content_hash": "conflictrec10a",
    "created_at": "2026-10-24T18:17:20Z",
    "updated_at": "2026-10-24T18:17:20Z",
    "is_representative": true,
    "group_id": "group-110",
    "group_members_count": 2,
    "query_versions": [
      1
    ],
    "current_decision": {
      "id": 610,
      "review_id": 1,
      "record_id": 110,
      "decision": "include",
      "reason_text": "Considered early T2D patients as eligible population",
      "reviewer": "Member A",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-24T18:56:00Z"
    }
  },
  {
    "id": 111,
    "review_id": 1,
    "source": "pubmed",
    "source_record_id": "35029999",
    "doi_norm": "10.1001/jamadiabetes.2022.04",
    "pmid": "35029999",
    "title": "Metformin Combined with Lifestyle Intervention vs Lifestyle Alone in Impaired Glucose Tolerance (Cohort B)",
    "title_norm": "metformin combined with lifestyle intervention vs lifestyle alone in impaired glucose tolerance",
    "abstract": "Randomized evaluation of metformin 500 mg plus dietary modification in 320 patients with impaired fasting glucose and early T2 diabetes.",
    "authors_json": [
      "Sharma R.",
      "Martinez L."
    ],
    "first_author_norm": "sharma",
    "year": 2022,
    "journal": "Lancet Diabetes & Endocrinology",
    "journal_norm": "lancet diabetes & endocrinology",
    "language": "eng",
    "pub_types_json": [
      "Randomized Controlled Trial"
    ],
    "mesh_json": [
      "Metformin",
      "Glucose Intolerance",
      "Humans"
    ],
    "content_hash": "conflictrec10b",
    "created_at": "2026-10-25T09:01:50Z",
    "updated_at": "2026-10-25T09:01:50Z",
    "is_representative": false,
    "group_id": "group-110",
    "group_members_count": 2,
    "query_versions": [
      2
    ],
    "current_decision": {
      "id": 611,
      "review_id": 1,
      "record_id": 111,
      "decision": "exclude",
      "criterion_id": 5,
      "reason_text": "Pre-diabetes population; does not satisfy manifest type 2 diabetes criterion",
      "reviewer": "Member C",
      "origin": "direct",
      "criteria_version_id": 1,
      "created_at": "2026-10-25T09:10:00Z"
    }
  }
];

export const mockDuplicatePairs: DuplicatePair[] = [
  {
    "id": 1,
    "review_id": 1,
    "record_a_id": 101,
    "record_b_id": 102,
    "method": "doi",
    "score": 1.0,
    "tier": "auto",
    "matched_fields_json": [
      "doi_norm",
      "pmid",
      "title_norm",
      "year",
      "first_author_norm"
    ],
    "conflicting_fields_json": [],
    "algo_version": "v1.0",
    "created_run_id": 1,
    "record_a": {
      "id": 107,
      "review_id": 1,
      "source": "europe_pmc",
      "source_record_id": "31458921",
      "doi_norm": "10.12659/amjcaserep.917821",
      "pmid": "31458921",
      "title": "Severe Lactic Acidosis Induced by Metformin Overdose in a 58-Year-Old Female with Type 2 Diabetes: A Case Report",
      "title_norm": "severe lactic acidosis induced by metformin overdose in a 58-year-old female with type 2 diabetes a case report",
      "abstract": "We report a case of severe metformin-associated lactic acidosis (MALA) in a 58-year-old female presenting with profound shock and metabolic acidosis after accidental overdose.",
      "authors_json": [
        "Lee J.",
        "Park S.",
        "Kim Y."
      ],
      "first_author_norm": "lee",
      "year": 2019,
      "journal": "American Journal of Case Reports",
      "journal_norm": "american journal of case reports",
      "volume": "20",
      "pages": "1245-1249",
      "language": "eng",
      "pub_types_json": [
        "Case Reports"
      ],
      "mesh_json": [
        "Metformin",
        "Acidosis, Lactic",
        "Humans",
        "Female"
      ],
      "content_hash": "leecase2019",
      "created_at": "2026-10-24T18:16:58Z",
      "updated_at": "2026-10-24T18:16:58Z",
      "is_representative": true,
      "group_id": "group-107",
      "group_members_count": 1,
      "query_versions": [
        1,
        2
      ],
      "suggestion": {
        "id": 505,
        "record_id": 107,
        "criteria_version_id": 1,
        "content_hash": "leecase2019",
        "algo_version": "v1.0",
        "suggestion": "exclude",
        "criterion_id": 3,
        "evidence_json": {
          "strength": "strong",
          "explanation": "Publication type is 'Case Reports'; describes individual patient.",
          "pub_type_hits": [
            "Case Reports"
          ],
          "regex_hits": [
            "we report a case",
            "a 58-year-old"
          ]
        },
        "created_at": "2026-10-24T18:17:00Z"
      },
      "current_decision": {
        "id": 607,
        "review_id": 1,
        "record_id": 107,
        "decision": "exclude",
        "criterion_id": 3,
        "reason_text": "Single patient case report; cannot demonstrate average treatment effect",
        "reviewer": "Member B",
        "origin": "direct",
        "criteria_version_id": 1,
        "created_at": "2026-10-24T18:45:00Z"
      }
    },
    "record_b": {
      "id": 108,
      "review_id": 1,
      "source": "europe_pmc",
      "source_record_id": "30109389",
      "doi_norm": "10.2196/12034",
      "pmid": "30109389",
      "title": "Projecting the 20-Year Cost-Effectiveness of Early Metformin: A Markov Microsimulation Model",
      "title_norm": "projecting the twenty-year cost-effectiveness of early metformin a markov microsimulation model",
      "abstract": "A discrete-event microsimulation Markov model was built using NHANES data to project cardiovascular events over 20 years. No direct patient trial measurements.",
      "authors_json": [
        "Johnson K.",
        "Williams P."
      ],
      "first_author_norm": "johnson",
      "year": 2019,
      "journal": "Medical Decision Making",
      "journal_norm": "medical decision making",
      "language": "eng",
      "pub_types_json": [
        "Journal Article"
      ],
      "mesh_json": [
        "Markov Chains",
        "Models, Statistical"
      ],
      "content_hash": "simulationmarkov",
      "created_at": "2026-10-24T18:17:05Z",
      "updated_at": "2026-10-24T18:17:05Z",
      "is_representative": true,
      "group_id": "group-108",
      "group_members_count": 1,
      "query_versions": [
        1,
        2
      ],
      "suggestion": {
        "id": 506,
        "record_id": 108,
        "criteria_version_id": 1,
        "content_hash": "simulationmarkov",
        "algo_version": "v1.0",
        "suggestion": "exclude",
        "criterion_id": 4,
        "evidence_json": {
          "strength": "weak",
          "explanation": "Rule detected computational simulation cues",
          "rule_hits": [
            "microsimulation",
            "Markov model"
          ]
        },
        "created_at": "2026-10-24T18:17:10Z"
      },
      "current_decision": {
        "id": 608,
        "review_id": 1,
        "record_id": 108,
        "decision": "exclude",
        "criterion_id": 4,
        "reason_text": "Computational Markov simulation without direct patient clinical measurements",
        "reviewer": "Member C",
        "origin": "direct",
        "criteria_version_id": 1,
        "created_at": "2026-10-24T18:50:00Z"
      }
    }
  },
  {
    "id": 2,
    "review_id": 1,
    "record_a_id": 103,
    "record_b_id": 104,
    "method": "title_year_author",
    "score": 0.88,
    "tier": "uncertain",
    "matched_fields_json": [
      "title_norm (fuzzy)",
      "first_author_norm"
    ],
    "conflicting_fields_json": [
      "pub_type: Journal Article vs Meeting Abstract",
      "year: 2017 vs 2016"
    ],
    "algo_version": "v1.0",
    "created_run_id": 1,
    "record_a": {
      "id": 109,
      "review_id": 1,
      "source": "europe_pmc",
      "source_record_id": "31600918",
      "doi_norm": "10.2196/pediatrics.2019-19",
      "pmid": "31600918",
      "title": "Metformin Therapy in Adolescents with Early-Onset Type 2 Diabetes: A Feasibility Pilot Trial",
      "title_norm": "metformin therapy in adolescents with early-onset type 2 diabetes a feasibility pilot trial",
      "abstract": "Pilot study evaluating metformin in 35 adolescents aged 12-17 years with confirmed risk factors. HbA1c decreased by 0.7%. Adult eligibility was not assessed.",
      "authors_json": [
        "Brown A.",
        "Evans T."
      ],
      "first_author_norm": "brown",
      "year": 2021,
      "journal": "Pediatric Diabetes",
      "journal_norm": "pediatric diabetes",
      "language": "eng",
      "pub_types_json": [
        "Journal Article"
      ],
      "mesh_json": [
        "Adolescent",
        "Metformin"
      ],
      "content_hash": "pediatricadolescent",
      "created_at": "2026-10-24T18:17:15Z",
      "updated_at": "2026-10-24T18:17:15Z",
      "is_representative": true,
      "group_id": "group-109",
      "group_members_count": 1,
      "query_versions": [
        1,
        2
      ],
      "suggestion": {
        "id": 507,
        "record_id": 109,
        "criteria_version_id": 1,
        "content_hash": "pediatricadolescent",
        "algo_version": "v1.0",
        "suggestion": "maybe",
        "criterion_id": null,
        "evidence_json": {
          "strength": "weak",
          "explanation": "Population is adolescents (12-17 years); unclear if meeting adult criterion",
          "rule_hits": [
            "adolescents aged 12-17 years"
          ]
        },
        "created_at": "2026-10-24T18:17:18Z"
      },
      "current_decision": {
        "id": 609,
        "review_id": 1,
        "record_id": 109,
        "decision": "maybe",
        "reason_text": "Adolescent pilot; pending consultation with lead reviewer regarding age cutoff",
        "reviewer": "Member D",
        "origin": "direct",
        "criteria_version_id": 1,
        "created_at": "2026-10-24T18:55:00Z"
      }
    },
    "record_b": {
      "id": 110,
      "review_id": 1,
      "source": "europe_pmc",
      "source_record_id": "35029998",
      "doi_norm": "10.1001/jamadiabetes.2022.04",
      "pmid": "35029998",
      "title": "Metformin Combined with Lifestyle Intervention vs Lifestyle Alone in Impaired Glucose Tolerance (Cohort A)",
      "title_norm": "metformin combined with lifestyle intervention vs lifestyle alone in impaired glucose tolerance",
      "abstract": "Randomized evaluation of metformin 500 mg plus dietary modification in 320 patients with impaired fasting glucose and early T2 diabetes.",
      "authors_json": [
        "Sharma R.",
        "Martinez L."
      ],
      "first_author_norm": "sharma",
      "year": 2022,
      "journal": "Lancet Diabetes & Endocrinology",
      "journal_norm": "lancet diabetes & endocrinology",
      "language": "eng",
      "pub_types_json": [
        "Randomized Controlled Trial"
      ],
      "mesh_json": [
        "Metformin",
        "Glucose Intolerance",
        "Humans"
      ],
      "content_hash": "conflictrec10a",
      "created_at": "2026-10-24T18:17:20Z",
      "updated_at": "2026-10-24T18:17:20Z",
      "is_representative": true,
      "group_id": "group-110",
      "group_members_count": 2,
      "query_versions": [
        1
      ],
      "current_decision": {
        "id": 610,
        "review_id": 1,
        "record_id": 110,
        "decision": "include",
        "reason_text": "Considered early T2D patients as eligible population",
        "reviewer": "Member A",
        "origin": "direct",
        "criteria_version_id": 1,
        "created_at": "2026-10-24T18:56:00Z"
      }
    }
  }
];

export const mockPairDecisions: PairDecision[] = [
  {
    "id": 1,
    "review_id": 1,
    "record_a_id": 101,
    "record_b_id": 102,
    "decision": "confirm",
    "note": "Exact identical trial; Europe PMC PMC record matches PubMed record 32928765",
    "reviewer": "Member C",
    "created_at": "2026-10-24T18:25:00Z",
    "superseded_by_id": null
  }
];

export const mockPicoAnnotations: PicoAnnotation[] = [
  {
    "id": 1,
    "record_id": 101,
    "label": "P",
    "text": "Adults with type 2 diabetes (n=1200)",
    "start_char": 0,
    "end_char": 36,
    "origin": "machine",
    "status": "suggested",
    "supersedes_id": null,
    "content_hash": "a1b2c3d4e5f6001",
    "algo_version": "v1.0",
    "reviewer": "System",
    "created_at": "2026-10-24T18:16:40Z"
  },
  {
    "id": 2,
    "record_id": 101,
    "label": "I",
    "text": "metformin 1000mg twice daily",
    "start_char": 46,
    "end_char": 74,
    "origin": "human",
    "status": "confirmed",
    "supersedes_id": null,
    "content_hash": "a1b2c3d4e5f6001",
    "algo_version": "v1.0",
    "reviewer": "Member D",
    "created_at": "2026-10-24T18:32:00Z"
  },
  {
    "id": 3,
    "record_id": 101,
    "label": "C",
    "text": "placebo",
    "start_char": 78,
    "end_char": 85,
    "origin": "human",
    "status": "confirmed",
    "supersedes_id": null,
    "content_hash": "a1b2c3d4e5f6001",
    "algo_version": "v1.0",
    "reviewer": "Member D",
    "created_at": "2026-10-24T18:32:00Z"
  },
  {
    "id": 4,
    "record_id": 101,
    "label": "O",
    "text": "change in HbA1c and incidence of microvascular complications",
    "start_char": 126,
    "end_char": 186,
    "origin": "machine",
    "status": "suggested",
    "supersedes_id": null,
    "content_hash": "a1b2c3d4e5f6001",
    "algo_version": "v1.0",
    "reviewer": "System",
    "created_at": "2026-10-24T18:16:40Z"
  }
];

export const mockConflicts: Conflict[] = [
  {
    "id": 1,
    "review_id": 1,
    "type": "group_decision_conflict",
    "fingerprint": "fp-conflict-rec110-111",
    "record_ids_json": [
      110,
      111
    ],
    "details_json": {
      "group_key": "grp-110-111-sharma",
      "records": [
        {
          "record_id": 110,
          "source": "europe_pmc",
          "title": "Metformin Combined with Lifestyle Intervention vs Lifestyle Alone in Impaired Glucose Tolerance (Cohort A)",
          "decision": "include",
          "reviewer": "Member A",
          "reason": "Considered early T2D patients as eligible population",
          "created_at": "2026-10-24T18:56:00Z"
        },
        {
          "record_id": 111,
          "source": "pubmed",
          "title": "Metformin Combined with Lifestyle Intervention vs Lifestyle Alone in Impaired Glucose Tolerance (Cohort B)",
          "decision": "exclude",
          "reviewer": "Member C",
          "reason": "Pre-diabetes population; does not satisfy manifest type 2 diabetes criterion",
          "created_at": "2026-10-25T09:10:00Z"
        }
      ],
      "merging_reason": "Identical DOI (10.1001/jamadiabetes.2022.04) and matching authors, but decided under separate query versions v1 and v2"
    },
    "status": "open",
    "created_run_id": 2,
    "resolved_at": null,
    "resolution_json": null,
    "reviewer": null
  }
];

export const mockRuns: PipelineRun[] = [
  {
    "id": 1,
    "review_id": 1,
    "query_version_id": 1,
    "trigger": "import",
    "active_version_ids_json": [
      1
    ],
    "status": "completed",
    "started_at": "2026-10-24T18:15:30Z",
    "finished_at": "2026-10-24T18:16:45Z",
    "error": null,
    "steps": [
      {
        "id": 1,
        "run_id": 1,
        "step": "fetch",
        "status": "completed",
        "started_at": "2026-10-24T18:15:30Z",
        "finished_at": "2026-10-24T18:16:00Z",
        "input_summary_json": {
          "source": "europe_pmc",
          "query": "(\"type 2 diabetes\" OR \"type II diabetes\") AND metformin AND placebo",
          "cap": 500
        },
        "output_summary_json": {
          "fetched_count": 500,
          "total_hits": 1842
        }
      },
      {
        "id": 2,
        "run_id": 1,
        "step": "store",
        "status": "completed",
        "started_at": "2026-10-24T18:16:01Z",
        "finished_at": "2026-10-24T18:16:10Z",
        "input_summary_json": {
          "records": 500
        },
        "output_summary_json": {
          "new_records": 500,
          "query_record_links": 500
        }
      },
      {
        "id": 3,
        "run_id": 1,
        "step": "dedup",
        "status": "completed",
        "started_at": "2026-10-24T18:16:11Z",
        "finished_at": "2026-10-24T18:16:20Z",
        "input_summary_json": {
          "active_records": 500
        },
        "output_summary_json": {
          "auto_pairs": 18,
          "uncertain_pairs": 4,
          "unique_groups": 478
        }
      },
      {
        "id": 4,
        "run_id": 1,
        "step": "reconcile",
        "status": "completed",
        "started_at": "2026-10-24T18:16:21Z",
        "finished_at": "2026-10-24T18:16:25Z",
        "input_summary_json": {
          "groups": 478
        },
        "output_summary_json": {
          "conflicts_opened": 0,
          "inherited_decisions": 0
        }
      },
      {
        "id": 5,
        "run_id": 1,
        "step": "screen",
        "status": "completed",
        "started_at": "2026-10-24T18:16:26Z",
        "finished_at": "2026-10-24T18:16:38Z",
        "input_summary_json": {
          "representatives": 478
        },
        "output_summary_json": {
          "suggest_include": 12,
          "suggest_exclude": 384,
          "suggest_maybe": 82
        }
      },
      {
        "id": 6,
        "run_id": 1,
        "step": "pico",
        "status": "completed",
        "started_at": "2026-10-24T18:16:39Z",
        "finished_at": "2026-10-24T18:16:44Z",
        "input_summary_json": {
          "eligible_records": 94
        },
        "output_summary_json": {
          "tagged_records": 94,
          "spans_extracted": 312
        }
      },
      {
        "id": 7,
        "run_id": 1,
        "step": "diff",
        "status": "completed",
        "started_at": "2026-10-24T18:16:44Z",
        "finished_at": "2026-10-24T18:16:45Z",
        "input_summary_json": {
          "prev_snapshot": null
        },
        "output_summary_json": {
          "initial_import": true,
          "records_added": 500
        }
      }
    ]
  },
  {
    "id": 2,
    "review_id": 1,
    "query_version_id": 2,
    "trigger": "import",
    "active_version_ids_json": [
      1,
      2
    ],
    "status": "completed",
    "started_at": "2026-10-25T09:00:30Z",
    "finished_at": "2026-10-25T09:02:15Z",
    "error": null,
    "steps": [
      {
        "id": 8,
        "run_id": 2,
        "step": "fetch",
        "status": "completed",
        "started_at": "2026-10-25T09:00:30Z",
        "finished_at": "2026-10-25T09:01:10Z",
        "input_summary_json": {
          "source": "europe_pmc",
          "query": "(\"type 2 diabetes\" OR \"type II diabetes\") AND metformin",
          "cap": 500
        },
        "output_summary_json": {
          "new_ids_fetched": 45,
          "known_ids_skipped": 455,
          "total_hits": 3410
        }
      },
      {
        "id": 9,
        "run_id": 2,
        "step": "store",
        "status": "completed",
        "started_at": "2026-10-25T09:01:11Z",
        "finished_at": "2026-10-25T09:01:20Z",
        "input_summary_json": {
          "new_records": 45
        },
        "output_summary_json": {
          "stored_new": 45,
          "query_record_links_added": 500
        }
      },
      {
        "id": 10,
        "run_id": 2,
        "step": "dedup",
        "status": "completed",
        "started_at": "2026-10-25T09:01:21Z",
        "finished_at": "2026-10-25T09:01:35Z",
        "input_summary_json": {
          "new_and_changed": 45,
          "active_total": 545
        },
        "output_summary_json": {
          "auto_pairs": 2,
          "groups_merged": 2
        }
      },
      {
        "id": 11,
        "run_id": 2,
        "step": "reconcile",
        "status": "completed",
        "started_at": "2026-10-25T09:01:36Z",
        "finished_at": "2026-10-25T09:01:45Z",
        "input_summary_json": {
          "groups_evaluated": 521
        },
        "output_summary_json": {
          "decisions_inherited": 42,
          "conflicts_opened": 1
        }
      },
      {
        "id": 12,
        "run_id": 2,
        "step": "screen",
        "status": "completed",
        "started_at": "2026-10-25T09:01:46Z",
        "finished_at": "2026-10-25T09:02:00Z",
        "input_summary_json": {
          "unscreened_reps": 3
        },
        "output_summary_json": {
          "suggest_include": 1,
          "suggest_exclude": 2,
          "suggest_maybe": 0
        }
      },
      {
        "id": 13,
        "run_id": 2,
        "step": "pico",
        "status": "completed",
        "started_at": "2026-10-25T09:02:01Z",
        "finished_at": "2026-10-25T09:02:10Z",
        "input_summary_json": {
          "eligible_reps": 1
        },
        "output_summary_json": {
          "tagged_records": 1,
          "spans_extracted": 4
        }
      },
      {
        "id": 14,
        "run_id": 2,
        "step": "diff",
        "status": "completed",
        "started_at": "2026-10-25T09:02:11Z",
        "finished_at": "2026-10-25T09:02:15Z",
        "input_summary_json": {
          "against_run_id": 1
        },
        "output_summary_json": {
          "diff_summary_saved": true
        }
      }
    ]
  }
];

export const mockDiffSummary: DiffSummary = {
  "from_version_id": 1,
  "to_version_id": 2,
  "records_added": 45,
  "records_removed": 0,
  "already_present": 500,
  "groups_merged": 2,
  "groups_split": 0,
  "decisions_preserved": 498,
  "decisions_inherited": 42,
  "conflicts_opened": 1,
  "needing_screening": 3
};

export const mockAuditEvents: AuditEvent[] = [
  {
    "id": 1,
    "review_id": 1,
    "actor": "reviewer:Member A",
    "action": "create_review",
    "entity_type": "review",
    "entity_id": 1,
    "before_json": null,
    "after_json": {
      "title": "Metformin vs Placebo in Type 2 Diabetes",
      "criteria_version": 1
    },
    "run_id": null,
    "created_at": "2026-10-24T18:00:00Z"
  },
  {
    "id": 2,
    "review_id": 1,
    "actor": "system",
    "action": "run_pipeline_completed",
    "entity_type": "pipeline_run",
    "entity_id": 1,
    "before_json": {
      "status": "importing"
    },
    "after_json": {
      "status": "completed",
      "fetched": 500,
      "unique_groups": 478
    },
    "run_id": 1,
    "created_at": "2026-10-24T18:16:45Z"
  },
  {
    "id": 3,
    "review_id": 1,
    "actor": "reviewer:Member C",
    "action": "confirm_duplicate_pair",
    "entity_type": "pair_decision",
    "entity_id": 1,
    "before_json": {
      "tier": "auto"
    },
    "after_json": {
      "decision": "confirm",
      "records": [
        101,
        102
      ],
      "note": "Exact identical trial in BMJ"
    },
    "run_id": null,
    "created_at": "2026-10-24T18:25:00Z"
  },
  {
    "id": 4,
    "review_id": 1,
    "actor": "reviewer:Member D",
    "action": "screening_decision",
    "entity_type": "screening_decision",
    "entity_id": 601,
    "before_json": {
      "current_decision": null
    },
    "after_json": {
      "decision": "include",
      "record_id": 101,
      "reason_text": "High quality randomized controlled trial"
    },
    "run_id": null,
    "created_at": "2026-10-24T18:30:00Z"
  },
  {
    "id": 5,
    "review_id": 1,
    "actor": "reviewer:Member B",
    "action": "screening_decision",
    "entity_type": "screening_decision",
    "entity_id": 605,
    "before_json": {
      "current_decision": null
    },
    "after_json": {
      "decision": "exclude",
      "criterion_id": 1,
      "reason_text": "Non-human animal study (Sprague-Dawley rats)"
    },
    "run_id": null,
    "created_at": "2026-10-24T18:35:00Z"
  },
  {
    "id": 6,
    "review_id": 1,
    "actor": "system",
    "action": "query_evolution_diff_computed",
    "entity_type": "diff_summary",
    "entity_id": 2,
    "before_json": {
      "version": 1
    },
    "after_json": {
      "version": 2,
      "records_added": 45,
      "conflicts": 1,
      "decisions_preserved": 498
    },
    "run_id": 2,
    "created_at": "2026-10-25T09:02:15Z"
  }
];
