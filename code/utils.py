import uuid
from urllib.parse import urlparse


def mint_dataset_id(ds_name):
    """Create a deterministic id based on a custom convention

    Uses "abcd-j.{ds_name}" as an input for UUID
    generation. Lowercases project. If there are multiple projects,
    uses the first one given.

    """

    dsid_input = {
        "name": ds_name,
    }
    dsid_config = {"dataset_id_fmt": "abcd-j.{name}"}

    return get_dataset_id(dsid_input, dsid_config)


def get_dataset_id(input, config):
    """Generate a v5 uuid"""
    # consult config for custom ID selection,
    # otherwise take plain standard field
    fmt = config.get("dataset_id_fmt", "{dataset_id}")
    # instantiate raw ID string
    raw_id = fmt.format(**input)
    # now turn into UUID deterministically
    return str(
        uuid.uuid5(
            uuid.uuid5(uuid.NAMESPACE_DNS, "datalad.org"),
            raw_id,
        )
    )

def process_authors(authors):
    """Convert author(s) to a list of catalog-schema authors"""
    known_keys = [
        "name",
        "email",
        "identifiers",
        "givenName",
        "familyName",
        "honorificSuffix",
    ]

    if authors is None:
        return None
    if isinstance(authors, dict):
        authors = [authors]

    result = []
    for author in authors:
        # drop not-known keys (like @type)
        d = {k: v for k, v in author.items() if k in known_keys and v is not None}
        # re-insert orcid as identifiers
        if orcid := author.get("orcid", False):
            d["identifiers"] = [
                {"name": "ORCID", "identifier": orcid},
            ]
        result.append(d)

    return result


def process_license(license):
    """Convert license to catalog-schema object

    Catalog schema expects name & url. We can reasonably expect
    schema:license to be a URL, but won't hurt checking. But what
    about the name?

    """
    if license is None:
        return None
    parsed_url = urlparse(license)
    if parsed_url.scheme != "" and parsed_url.netloc != "":
        # looks like a URL
        pass

    # do the least work, for now
    return {"name": license, "url": license}


def process_publications(publications):
    """Convert publication to catalog-schema object

    Catalog schema expects title, doi, datePublished,
    publicationOutlet, & authors. Our tabby spec only makes "citation"
    required, and allows doi, url, and datePublished (if doi is given,
    citation becomes optional).

    Best thing we can do in the citation-only case is to squeeze
    citation into title (big text that's displayed).

    When DOI is given, we can look it up to get all fields, and it's
    our artistic license whether citation should take precedence or
    not.

    """
    if publications is None:
        return None
    if type(publications) is dict:
        publications = [publications]

    res = []
    for publication in publications:
        citation = publication.pop("citation", None)

        if citation is not None:
            publication["title"] = citation
            publication["authors"] = []

        # todo: doi lookup
        res.append(publication)

    return res


def process_funding(funding):
    """Ensure that funding is an array"""
    return [funding] if isinstance(funding, dict) else funding


def process_keywords(keywords):
    """Ensure that keywords are an array"""
    return [keywords] if isinstance(keywords, str) else keywords


def process_arc(data_controller):
    """Convert data controller to access request contact

    Since there can only be one, uses the first data
    controller. Splits name (very naively) to satisfy catalog
    schema. Oblivious to the fact that the controller needs not be a
    person.

    """
    if data_controller is None:
        return None
    if isinstance(data_controller, list):
        data_controller = data_controller[0]

    first, _, last = data_controller.get("name", "").rpartition(" ")
    email = data_controller.get("email", "")

    return {"givenName": first, "familyName": last, "email": email}


def process_data_controller(data_controller):
    """Convert data controller to a dict or list of dict

    Adds schema.org Person type (which means we assume all data
    controllers to be persons) for linked data scenarios.

    """
    if data_controller is None:
        return None
    if isinstance(data_controller, list):
        return [process_data_controller(dc) for dc in data_controller]

    return {"@type": "https://schema.org/Person"} | data_controller


def process_used_for(activity):
    """Change an activity-dict to a schema.org Thing

    The activity coming from SFB1451-tabby has a title, description,
    and URL. We will use a generic schema.org Thing to report these
    properties and allow the catalog to display them nicely.

    """
    if isinstance(activity, list):
        return [process_used_for(act) for act in activity]
    if activity is None:
        return None

    thing = {"@type": "https://schema.org/Thing"}
    thing["name"] = activity.get("title", "")

    if url := activity.get("url", False):
        thing["url"] = url

    if description := activity.get("description", False):
        if type(description) is list:
            # we allowed multi-paragraph entries across columns
            # which we now join using newlines to avoid having
            # to add paragraphs in the catalog
            description = "\n\n".join(description)
        thing["description"] = description

    return thing


def process_file(f):
    """Convert file information to catalog schema

    This gets item values (or @values, depending how they were defined
    in tabby expansion context), and does type conversion (bytesize to
    int). Returns a dictionary with catalog keys that can be read from
    tabby (does not contain type and dataset id/version).

    """
    d = {
        "path": f.get("path", {}).get("@value"),
        "contentbytesize": f.get("contentbytesize", {}).get("@value"),
        "url": f.get("url"),
    }

    if f.get("path") is None and f.get("name") is not None:
        # scoped context definition doesn't work for me as intended,
        # no idea why -- this would cover all bases
        d["path"] = f.get("name", {}).get("@value")

    if d.get("contentbytesize", False):
        # type conversion
        d["contentbytesize"] = int(d["contentbytesize"])

    return {k: v for k, v in d.items() if v is not None}


def process_homepage(homepage):
    """Return homepage as a dict or list of dict

    Returned dict will contain schema.org @type (URL) for usage in
    linked data scenarios.

    """
    if homepage is None:
        return None
    elif isinstance(homepage, list):
        return [process_homepage(hp) for hp in homepage]
    else:
        return {"@type": "https://schema.org/URL", "@value": homepage}
    

def process_subdatasets(subdatasets):
    """Convert subdatasets to a list with items in the expected format

    """
    if subdatasets is None:
        return []
    if isinstance(subdatasets, list):
        return [dict(
            dataset_id=subds.get("identifier"),
            dataset_version=subds.get("version"),
            dataset_path=subds.get("path_posix"),
            dataset_url=subds.get("url"),
        ) for subds in subdatasets]
    if isinstance(subdatasets, dict):
        return [dict(
            dataset_id=subdatasets.get("identifier"),
            dataset_version=subdatasets.get("version"),
            dataset_path=subdatasets.get("path_posix"),
            dataset_url=subdatasets.get("url"),
        )]


CAT_CONTEXT = {
    "schema": "https://schema.org/",
    "afo": "http://purl.allotrope.org/ontologies/result#",
    "bibo": "https://purl.org/ontology/bibo/",
    "dcterms": "https://purl.org/dc/terms/",
    "nfo": "https://www.semanticdesktop.org/ontologies/2007/03/22/nfo/#",
    "obo": "https://purl.obolibrary.org/obo/",
    "openminds": "https://openminds.ebrains.eu/controlledTerms/",
    "name": "schema:name",
    "title": "schema:title",
    "description": "schema:description",
    "doi": "bibo:doi",
    "version": "schema:version",
    "license": "schema:license",
    "description": "schema:description",
    "authors": "schema:author",
    "orcid": "obo:IAO_0000708",
    "email": "schema:email",
    "keywords": "schema:keywords",
    "funding": {
        "@id": "schema:funding",
        "@context": {
            "name": "schema:funder",
            "identifier": "schema:identifier",
        },
    },
    "publications": {
        "@id": "schema:citation",
        "@context": {
            "doi": "schema:identifier",
            "datePublished": "schema:datePublished",
            "citation": "schema:citation",
        },
    },
    "fileList": {
        "@id": "dcterms:hasPart",
        "@context": {
            "contentbytesize": "nfo:fileSize",
            "md5sum": "obo:NCIT_C171276",
            "path": "schema:name",
            "url": "schema:contentUrl",
        },
    },
    "subdatasets": {
        "@id": "schema:Dataset",
        "@context": {
            "dataset_type": "schema:Text",
            "identifier": "schema:identifier",
            "path_posix": "afo:AFR_0001928",
            "version": "schema:version",
            "url": "schema:contentUrl"
        }
    },
    "address": "schema:PostalAddress",
    "homepage": "schema:mainEntityOfPage",
    "dataController": "https://w3id.org/dpv#hasDataController",
    "usedFor": {
        "@id": "http://www.w3.org/ns/prov#hadUsage",
        "@context": {
            "url": "schema:url",
        },
    },
    "sampleOrganism": "openminds:Species",
    "samplePart": "openminds:UBERONParcellation",
}