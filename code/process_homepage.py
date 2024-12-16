from argparse import ArgumentParser
import json
from pathlib import Path

from datalad_catalog.extractors import catalog_core
from datalad_next.constraints.dataset import EnsureDataset

from get_tabby_metadata import get_tabby_metadata



def get_super_metadata(dataset):
    """"""
    # first get core dataset-level metadata
    core_record = catalog_core.get_catalog_metadata(dataset)
    # then get tabby metadata
    tabby_record = get_tabby_metadata(
        tabby_path=None,
        dataset_path=dataset.pathobj,
        id_source='datalad_dataset',
        convention='tby-r2d2v0')
    # return both, and dataset
    return core_record, tabby_record


def add_super_to_catalog(core_record, tabby_records, ds):
    repo_path = Path(__file__).resolve().parent.parent
    from datalad.api import  (
        catalog_add,
        catalog_set,
    )
    catalog_dir = repo_path / 'catalog'
    # Add core metadata to the catalog
    catalog_add(
        catalog=catalog_dir,
        metadata=json.dumps(core_record),
        config_file = repo_path / 'inputs' / 'superds-config.json',
    )
    # Add tabby metadata to the catalog
    for r in tabby_records:
        catalog_add(
            catalog=catalog_dir,
            metadata=json.dumps(r),
            config_file = repo_path / 'inputs' / 'superds-config.json',
        )
    # Set the catalog home page
    catalog_set(
        catalog=catalog_dir,
        property="home",
        dataset_id=ds.id,
        dataset_version=ds.repo.get_hexsha(),
        reckless="overwrite",
    )
    


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument(
        "dataset_path", type=str, help="Path to the parent datalad dataset",
    )
    parser.add_argument("--add-to-catalog", action="store_true")
    args = parser.parse_args()
    # Ensure is a dataset
    ds = EnsureDataset(
        installed=True, purpose="extract core metadata", require_id=True
    )(args.dataset_path).ds

    core_record, tabby_records = get_super_metadata(ds)
    
    print(json.dumps(core_record))
    print("\n")
    print(json.dumps(tabby_records))

    # Add metadata to catalog if so specified
    if args.add_to_catalog:
        add_super_to_catalog(core_record, tabby_records, ds)

    