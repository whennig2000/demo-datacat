"""
Get tabby metadata from a datalad dataset
"""
from argparse import ArgumentParser
import json
from pathlib import Path
from pyld import jsonld
import pprint

from datalad_catalog.schema_utils import (
    get_metadata_item,
)
from datalad_next.constraints.dataset import EnsureDataset
from datalad_tabby.io import load_tabby

from utils import (
    CAT_CONTEXT,
    mint_dataset_id,
    process_arc,
    process_authors,
    process_data_controller,
    process_file,
    process_funding,
    process_homepage,
    process_keywords,
    process_license,
    process_publications,
    process_subdatasets,
    process_used_for,
)

from queries import (
    process_ols_term,
    repr_ncbitaxon,
    repr_uberon,
)

def get_tabby_metadata(tabby_path, dataset_path=None, id_source='tabby_mint', convention='tby-abcdjv0'):
    # Provide EITHER tabby_path OR dataset_path

    # Some validation
    if dataset_path is not None:
        dataset = EnsureDataset(
            installed=True, purpose="extract tabby metadata", require_id=True
        )(dataset_path).ds
        tabby_path = dataset.pathobj / f'.datalad/tabby/self/dataset@{convention}.tsv'
        assert tabby_path.exists()
        if id_source != "datalad_dataset":
            print(f"WARNING: argument 'id-source' provided/defaulted as '{id_source}' but setting it to 'datalad_dataset' "
                "since the path to a datalad dataset with a self-describing tabby record was provided")
            id_source = "datalad_dataset"
    else:
        dataset = None
        tabby_path = Path(tabby_path)
        assert tabby_path.exists()

    # Load tabby record
    repo_path = Path(__file__).resolve().parent.parent
    meta_record = load_tabby(
        src=tabby_path,
        single=True,
        jsonld=True,
        recursive=True,
        cpaths=[repo_path / 'inputs'],
    )

    # Json-ld stuff
    expanded = jsonld.expand(meta_record)
    compacted = jsonld.compact(meta_record, ctx=CAT_CONTEXT)

    # Determine dataset id and version from "id_source"
    if id_source == "tabby_mint":
        # mint uuid from the 'name' field
        dataset_id = mint_dataset_id(compacted.get("name"))
        dataset_version = compacted.get("version", "latest")
    if id_source == "tabby_direct":
        # get id directly from the 'name' field
        dataset_id = compacted.get("name")
        dataset_version = compacted.get("version", "latest")
    if id_source == "datalad_dataset":
        # grab id from the associated datalad dataset
        dataset_id = dataset.id
        dataset_version = dataset.repo.get_hexsha()
    
    # Use catalog schema_utils to get base structure of metadata item
    meta_item = get_metadata_item(
        item_type='dataset',
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        source_name="tabby",
        source_version="0.1.0",
    )
    # add properties for the catalog record
    meta_item["name"] = compacted.get("title", "")
    meta_item["license"] = process_license(compacted.get("license"))
    meta_item["description"] = compacted.get("description", "")
    meta_item["doi"] = compacted.get("doi", "")
    meta_item["authors"] = process_authors(compacted.get("authors"))
    meta_item["keywords"] = process_keywords(compacted.get("keywords"))
    meta_item["funding"] = process_funding(compacted.get("funding"))
    meta_item["publications"] = process_publications(compacted.get("publications"))
    meta_item["access_request_contact"] = process_arc(compacted.get("dataController"))
    meta_item["subdatasets"] = process_subdatasets(compacted.get("subdatasets"))
    meta_item["url"] = compacted.get("homepage", None)
    # add 'additional display' properties
    # note: to avoid having to do fancy expansion tricks in the catalog to show IRIs
    # as functioning links, we are providing context explicitly here
    additional_content = {
        "@context": {
            "homepage": "https://schema.org/mainEntityOfPage",
            "data controller": "https://w3id.org/dpv#hasDataController",
            "sample (organism)": "https://openminds.ebrains.eu/controlledTerms/Species",
            "sample (organism part)": "https://openminds.ebrains.eu/controlledTerms/UBERONParcellation",
            "used for": "http://www.w3.org/ns/prov#hadUsage",
        },
        "sample (organism)": process_ols_term(
            compacted.get("sampleOrganism"),
            repr_ncbitaxon,
        ),
        "sample (organism part)": process_ols_term(
            compacted.get("samplePart"),
            repr_uberon,
        ),
        "homepage": process_homepage(compacted.get("homepage")),
        "data controller": process_data_controller(compacted.get("dataController")),
        "used for": process_used_for(compacted.get("usedFor")),
    }
    # define an additional display tab for sfb content
    meta_item["additional_display"] = [
        {
            "name": "ABCD-J",
            "icon": "fa-solid fa-graduation-cap",
            "content": {k: v for k, v in additional_content.items() if v is not None},
        }
    ]
    # Remove empty properties from the dataset metadata
    meta_item = {k: v for k, v in meta_item.items() if v is not None}

    # ---
    # File handling
    # File handling's different, because 1 file <-> 1 metadata object
    # ---
    # some metadata is constant for all files
    # we copy dataset id & version from (dataset-level) meta_item
    file_required_meta = get_metadata_item(
        item_type='file',
        dataset_id=meta_item.get("dataset_id"),
        dataset_version=meta_item.get("dataset_version"),
        source_name="tabby",
        source_version="0.1.0",
        exclude_keys=["path"],
    )
    # make a list of catalog-conforming dicts
    cat_file_listing = []
    all_files = compacted.get('fileList', [])
    if not isinstance(all_files, list):
        all_files = [all_files]
    
    for file_info in all_files:
        cat_file = file_required_meta | process_file(file_info)
        cat_file_listing.append(cat_file)
    
    return [meta_item] + cat_file_listing


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument(
        "--tabby-path", type=Path, help="Path to the tabby dataset file"
    )
    parser.add_argument(
        "--dataset-path", type=Path, help="Path to a datalad dataset with self-describing tabby file(s)"
    )
    parser.add_argument(
        "--id-source", type=str, choices={"tabby_mint", "tabby_direct", "datalad_dataset"},
        default="tabby_mint",
        help=("What should be the source of the ID and VERSION "
              "that end up in the output record. One of: "
              "('tabby_mint', 'tabby_direct', 'datalad_dataset') ")
    )
    args = parser.parse_args()

    if not args.tabby_path and not args.dataset_path:
        raise TypeError("Either a path to a dataset with self-describing tabby files OR "
                        "a path to the root element of a set of tabby files has to be provided.")
    
    if args.tabby_path and args.dataset_path:
        raise TypeError("Please provide EITHER a path to a dataset with self-describing tabby files OR "
                        "a path to the root element of a set of tabby files")

    meta_item = get_tabby_metadata(args.tabby_path, args.dataset_path, args.id_source)
    print(meta_item)