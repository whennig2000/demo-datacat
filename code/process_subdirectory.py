from argparse import ArgumentParser
import csv
import json
from pathlib import Path

from datalad_next.constraints.dataset import EnsureDataset

from get_tabby_metadata import get_tabby_metadata
from process_homepage import get_super_metadata


if __name__ == "__main__":
    # Argument parsing and validation
    parser = ArgumentParser()
    parser.add_argument(
        "dataset_path", type=str, help="Path to the datalad superdataset",
    )
    parser.add_argument(
        "subdir_path", type=str, help="Relative path to subdirectory containing tabby files",
    )
    parser.add_argument(
        "--dataset-type", type=str, choices={"datalad", "other"},
        default="other",
        help="Is the described dataset a datalad dataset or other?"
    )
    parser.add_argument("--add-to-catalog", action="store_true")
    parser.add_argument("--hide-access-request", action="store_true")
    parser.add_argument(
        "--ignore-super",
        action="store_true",
        help="""If provided, do not try to add subdataset to superdataset tabby files,
        and do not re-extract and re-add the superdataset metadata""")
    parser.add_argument(
        "--add-type", type=str, choices={"dataset", "file", "both"},
        default="both",
        help="Which metadata to extract from tabby files and add to catalog"
    )
    
    args = parser.parse_args()
    ds = EnsureDataset(
        installed=True, purpose="get subdirectory metadata", require_id=True
    )(args.dataset_path).ds
    repo_path = Path(__file__).resolve().parent.parent
    
    # 1. Get tabby metadata from files at 'subdir_path'. This metadata
    #    describes a dataset that will be added as a subdataset to the
    #    catalog superdataset.
    tabby_path = Path(args.dataset_path) / args.subdir_path / 'dataset@tby-abcdjv0.tsv'
    assert tabby_path.exists()
    subds_tabby_records = get_tabby_metadata(
        tabby_path=tabby_path,
        dataset_path=None,
        id_source='tabby_direct' if args.dataset_type == 'datalad' else 'tabby_mint')
    
    # 2. Create subdataset record to be added to superdataset tabby file:
    #    - get the subdataset id, version, and url from the dataset-level
    #      record contained in the returned list of tabby metadata
    #    - get the subdataset path from supplied argument
    #    - get the subdataset type from supplied argument
    subdataset_record = [r for r in subds_tabby_records if r["type"] == "dataset"]
    assert len(subdataset_record) == 1
    subds_id = subdataset_record[0]["dataset_id"]
    subds_version = subdataset_record[0]["dataset_version"]
    subds_url = subdataset_record[0].get("url")
    subds_path = args.subdir_path
    subdataset = {
        "dataset_type": "DATALAD" if args.dataset_type == "datalad" else "OTHER",
        "identifier": subds_id,
        "version": subds_version,
        "path_posix": subds_path,
    }
    # Only include URL if it is a datalad dataset
    if args.dataset_type == "datalad":
        subdataset["url"] = subds_url

    # 3. Now add subdataset record to the superdataset tabby file at
    #    '<superdataset>/.datalad/tabby/self/subdatasets@tby-abcdjv0.tsv'
    # - First get the home page tabby record
    home_tabby_record = get_tabby_metadata(
        tabby_path=None,
        dataset_path=repo_path / 'data',
        id_source='datalad_dataset')
    # - Then get existing subdatasets from this home record
    home_dataset_record = [r for r in home_tabby_record if r["type"] == "dataset"]
    assert len(home_dataset_record) == 1
    existing_subdatasets = home_dataset_record[0].get("subdatasets", [])
    # - Now check if the exact subdataset record is already part of the list of subdatasets
    find_subdataset = [s for s in existing_subdatasets
                       if s["dataset_id"] == subds_id
                       and s["dataset_version"] == subds_version
                       and s["dataset_path"] == subds_path]
    # - Also check for existing subdataset (same id and path) with a prior version
    find_subds_prior = [s for s in existing_subdatasets
                       if s["dataset_id"] == subds_id
                       and s["dataset_version"] != subds_version
                       and s["dataset_path"] == subds_path]
    # If exact subdataset exists in the list:
    # - do nothing
    # If subdataset doesn't exist in the list:
    # - if subdatasets tabby file exists, append row or replace existing subds with different version
    # - if subdatasets tabby file does not exist, create with single row
    fieldnames = ["dataset_type", "identifier", "version", "path_posix", "url"]
    subdatasets_tabby_path = Path(args.dataset_path) / f'.datalad/tabby/self/subdatasets@tby-abcdjv0.tsv'
    if len(find_subdataset) == 0 and not args.ignore_super:
        subdataset_added = True
        # If there's no tabby file, create one and add header and then row
        if not subdatasets_tabby_path.exists():
            with subdatasets_tabby_path.open("w", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, delimiter="\t", fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(subdataset)
        else:
            # If there IS a tabby file, first read all rows
            with subdatasets_tabby_path.open("r") as csvfile_in:
                all_rows = []
                for row in csv.DictReader(csvfile_in, delimiter="\t"):
                    all_rows.append(row)
                # then check if the same subdataset with different version is already in the list
                prior_subds_i = next((i for i, item in enumerate(all_rows)
                                    if item["identifier"] == subds_id
                                    and item["version"] != subds_version
                                    and item["path_posix"] == subds_path
                                    ), -1)
                if prior_subds_i > -1:
                    # If in the list, replace previous subdataset entry with new version
                    all_rows[prior_subds_i] = subdataset
                else:
                    # If not in the list, append the new subdataset
                    all_rows.append(subdataset)
            # Then write the updated list to file
            with subdatasets_tabby_path.open("w", encoding="utf-8", newline="") as csvfile_out:
                writer = csv.DictWriter(csvfile_out, delimiter="\t", fieldnames=fieldnames)
                writer.writeheader()
                for r in all_rows:
                    writer.writerow(r)
    else:
        subdataset_added = False   
    # 4. Save the datalad superdataset:
    # - if the subdataset was added after updating the tabby files
    # - if the --ignore-super flag was not provided  
    if subdataset_added and not args.ignore_super:
        ds.save(
            message=f"Adds new sub-directory ({args.subdir_path}) as a subdataset in tabby metadata",
            to_git=True,
        )
    # 5. Get (possibly updated) homepage metadata
    home_core_record, home_tabby_records = get_super_metadata(ds)
    
    # 6. Add all records to catalog:
    # - if specified via 'add_to_catalog' argument
    # - depending on the --add-type argument (dataset / files / both)
    if args.add_to_catalog:
        from datalad.api import  (
            catalog_add,
            catalog_set,
        )
        catalog_dir = repo_path / 'catalog'
        if not args.ignore_super:
            # Add superdataset core metadata to the catalog
            catalog_add(
                catalog=catalog_dir,
                metadata=json.dumps(home_core_record),
                config_file = repo_path / 'inputs' / 'superds-config.json',
            )
            # Add superdataset tabby metadata to the catalog
            for r in home_tabby_records:
                catalog_add(
                    catalog=catalog_dir,
                    metadata=json.dumps(r),
                    config_file = repo_path / 'inputs' / 'superds-config.json',
                )
        # get correct config
        cfg_fname = 'subds-config.json'
        if args.hide_access_request:
            cfg_fname = 'subds-config-hide-access-request.json'
        # Add subdataset tabby metadata to the catalog, depending on --add-type
        if args.add_type == 'both':
            subds_records_to_add = subds_tabby_records
        else:
            subds_records_to_add = [r for r in subds_tabby_records if r["type"] == args.add_type]
        for r in subds_records_to_add:
            catalog_add(
                catalog=catalog_dir,
                metadata=json.dumps(r),
                config_file = repo_path / 'inputs' / cfg_fname,
            )

        if not args.ignore_super:
            # 7. Set new catalog homepage
            catalog_set(
                catalog=catalog_dir,
                property="home",
                dataset_id=home_core_record["dataset_id"],
                dataset_version=home_core_record["dataset_version"],
                reckless="overwrite",
            )