# The R2D2 Catalog

This repository contains the sources and content for the R2D2 Data Catalog hosted at: https://data.r2d2.de/

For more information about the R2D2 project, visit the website at: https://www.r2d2-mh.eu/collaborations/

---

## Repository Layout

`./catalog`
- data catalog sources
- the live catalog site serves this directory

`./code`
- scripts that are used for catalog updates

`./data`
- homepage of the catalog

`./inputs`
- input files used during catalog creation, updates, and testing



- Linkage of a subdirectory with tabby records to the datalad superdataset can be done by adding the relevant information from the subdirectory's tabby records to the `subdatasets@tby-r2d2v0.tsv` file of the superdataset's self-describing tabby records. 

## How to update the catalog

### (Re)create the catalog

```
datalad catalog-create --catalog catalog --config-file inputs/catalog-config.json --force
```

### (Re)add the homepage metadata

after updating `tabby` files in `data/.datalad/tabby/self/`

```
python code/process_homepage.py data --add-to-catalog
```

This will:
- run `code/process_homepage.py`
- extract the updated homepage metadata from tabby files at `data/.datalad/tabby/self/`
- transform this metadata to be compatible with the catalog schema
- add the catalog-compatible entry to the catalog (if the `--add-to-catalog` flag is provided)
- reset the catalog homepage to the updated version
- add a new commit to this repository containing these changes

! push to here


### Collecting new dataset metadata

- get excel sheet
- add the rows in the table below to the `dataset` sheet of the document provided by the user. These are necessary for `datalad-tabby` to import other sheets into the parent `dataset` sheet, so that metadata from all provided sheets can be loaded correctly. These rows are not included in the template doc provided to users so as not to confuse them with unnecessary technical content.

    | column 1 | column 2 |
    | - | - |
    | authors | @tabby-many-authors@tby-r2d2v0 |
    | data-controller | @tabby-optional-many-data-controller@tby-r2d2v0 |
    | files | @tabby-optional-many-files@tby-ds1 |
    | funding | @tabby-optional-many-funding@tby-r2d2v0 |
    | publication | @tabby-optional-many-publications@tby-r2d2v0 |
    | subdatasets | @tabby-optional-many-subdatasets@tby-r2d2v0 |
    | used-for | @tabby-optional-many-used-for@tby-r2d2v0 |

- export all sheets of the document separately as TSV files. Then ensure that all of these TSV files have the correct names (identical to the sheets they were exported from), and that each filename is appended with the tabby convention used in the process of loading metadata from these files. You should end up with a list of files similar to the following:
   - `authors@tby-r2d2v0.tsv`
   - `data-controller@tby-r2d2v0.tsv`
   - `dataset@tby-r2d2v0.tsv`
   - `files@tby-ds1.tsv`
   - `funding@tby-r2d2v0.tsv`
   - `publication@tby-r2d2v0.tsv`
   - `subdatasets@tby-r2d2v0.tsv`
   - `used-for@tby-r2d2v0.tsv`

### Add new dataset metadata to `data`

- create a new dataset directory inside the relevant institute directory
- move all the TSV files into this new directory
- commit these changes to git
- push the commit to the remote `origin`

### Add a new dataset to the catalog

```
python code/process_subdirectory.py data <relative-path-to-new-dataset> --dataset-type <new-dataset-type> --add-to-catalog
```

- `python code/process_subdirectory.py data`: this is the script that does all the work, and its main argument points to the homepage dataset, located at `data` (relative to the current repository root)
- `<relative-path-to-new-dataset>`: should be replaced by your new dataset directory location relative to the `data` dataset root. For the example used previously in relation to the file tree, it would be `FZJ/jumax`.
- `--dataset-type <new-dataset-type>`: this is used to help the script know what to do with the `name` field provided by the user in the `dataset@tby-r2d2v0.tsv` sheet. See https://rdm.r2d2.de/instructions.html#dataset-required:

   > If the dataset is structured as a DataLad dataset, the name property should be the DataLad dataset ID, and the type property should be datalad.
  
  The value of `<new-dataset-type>` will either be `datalad` or `other` (the latter, most likely) *(TODO: this is an example of a step that must still be automated)*
- `--add-to-catalog`: This flag adds all generated entries to the catalog.

### example

```
datalad run -m "Extract new dataset metadata from tabby records and add entries to catalog" -i "inputs/*" -o "catalog/*" --assume-ready both "python code/process_subdirectory.py data FZJ/jumax --dataset-type datalad --add-to-catalog"
```

This code will:
- run the script at `code/process_subdirectory.py`
- extract the new dataset metadata from tabby files at `data/FZJ/jumax/*`
- transform this extracted metadata to be compatible with the catalog schema
- extract the homepage metadata from tabby files at 
- add the new dataset (id and version) as a new subdataset to the homepage metadata in tabby files at `data/.datalad/tabby/self/*`
- save the updated homepage dataset at `data` (i.e. the DataLad subdataset of the current repository)
- add the new dataset's catalog-compatible entries to the catalog (if the `--add-to-catalog` flag is provided)
- reset the catalog homepage to the updated version (after adding a new subdataset)
- add a new commit to the current repository containing all these changes

push to here