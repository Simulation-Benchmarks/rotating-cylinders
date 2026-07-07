"""Helpers for querying benchmark provenance from RoHub."""

from __future__ import annotations

from collections.abc import Sequence
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Iterable
import pandas as pd
import rohub


CONFIG_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = CONFIG_DIR.parent
LOGGER = logging.getLogger(__name__)


def _load_json_config(filename: str) -> dict:
    """Load a JSON config file from the provenance package directory."""
    with (CONFIG_DIR / filename).open(encoding="utf-8") as config_file:
        return json.load(config_file)


ROHUB_CONFIG = _load_json_config("rohub_config.json")
ANNOTATION_CONFIG = _load_json_config("annotation_config.json")
ANNOTATION_PREDICATE = ANNOTATION_CONFIG["predicate"]
CODE_REPOSITORY_PREDICATE = "https://schema.org/codeRepository"
SOFTWARE_USED_PREDICATE = "http://www.w3.org/ns/prov#used"


SCHEMA_PREFIX = "PREFIX schema: <http://schema.org/>"
FORMAL_PARAMETER_TYPE = "<https://bioschemas.org/FormalParameter>"
FOAF_NAME = "<http://xmlns.com/foaf/0.1/name>"


def sanitize_variable_name(name: str) -> str:
    """Convert a string into a SPARQL-safe variable name."""
    variable_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if re.match(r"^\d", variable_name):
        variable_name = "_" + variable_name
    return variable_name or "_"


def _sparql_string_literal(value: str) -> str:
    """Escape a Python string for safe use inside a SPARQL string literal."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _variable_map(names: Iterable[str]) -> dict[str, str]:
    """Map display names to SPARQL-safe variable names."""
    return {name: sanitize_variable_name(name) for name in names}


def _select_variables(names: Sequence[str], var_map: dict[str, str]) -> str:
    """Create a SPARQL SELECT variable list from display names."""
    return " ".join(f"?{var_map[name]}" for name in names)


def _create_action_links(include_tool: bool = False) -> list[str]:
    """Build the common CreateAction graph pattern."""
    links = [
        "?runAction a schema:CreateAction .",
        "?runAction schema:object ?configuration .",
        "?configuration a schema:PropertyValue .",
    ]

    if include_tool:
        links.extend(
            [
                "?software a schema:SoftwareApplication .",
                f"?software {FOAF_NAME} ?tool_name .",
            ]
        )

    return links


def _node_type(node_prefix: str) -> str:
    """Return the RDF type used by a parameter or metric node."""
    if node_prefix == "param":
        return FORMAL_PARAMETER_TYPE
    return "schema:PropertyValue"


def _value_block(
    parent: str,
    relation: str,
    node_prefix: str,
    name: str,
    var_map: dict[str, str],
    name_predicate: str,
) -> str:
    """Build a graph pattern that extracts one named value."""
    safe_name = var_map[name]
    escaped_name = _sparql_string_literal(name)

    return f"""
    {parent} {relation} ?{node_prefix}_{safe_name} .
    ?{node_prefix}_{safe_name} a {_node_type(node_prefix)} ;
        {name_predicate} "{escaped_name}" ;
        schema:defaultValue ?{safe_name} .
    """.strip()


def _parameter_block(
    name: str,
    var_map: dict[str, str],
    name_predicate: str = "schema:name",
) -> str:
    """Build a graph pattern that extracts one configuration parameter."""
    return _value_block(
        "?configuration",
        "schema:exampleOfWork",
        "param",
        name,
        var_map,
        name_predicate,
    )


def _metric_block(
    name: str,
    var_map: dict[str, str],
    name_predicate: str = "schema:name",
) -> str:
    """Build a graph pattern that extracts one run metric."""
    return _value_block(
        "?runAction",
        "schema:result",
        "metric",
        name,
        var_map,
        name_predicate,
    )


def _join_blocks(*blocks: str) -> str:
    """Join non-empty SPARQL graph pattern blocks."""
    return "\n".join(block for block in blocks if block)


def _named_graph_values_block(
    named_graphs: Sequence[str],
    inner_query: str,
) -> str:
    """Wrap a query in ``VALUES ?graph`` and ``GRAPH ?graph`` clauses."""
    if not named_graphs:
        return inner_query

    values_block = "VALUES ?graph {\n" + "\n".join(
        f"    <{graph}>" for graph in named_graphs
    ) + "\n}"

    return f"""
    {values_block}

    GRAPH ?graph {{
        {inner_query}
    }}
    """.strip()


def _order_clause(
    order_name: str | None,
    var_map: dict[str, str],
) -> str:
    """Build an ORDER BY clause for a selected parameter or metric."""
    if not order_name:
        return ""

    order_var = var_map.get(order_name, sanitize_variable_name(order_name))
    return f"\nORDER BY ?{order_var}"


def _format_query(
    select_vars: str,
    where_block: str,
    order_clause: str = "",
) -> str:
    """Format a complete SPARQL query."""
    return f"""
    {SCHEMA_PREFIX}

    SELECT {select_vars}
    WHERE {{
        {where_block}
    }}
    {order_clause}
    """.strip()


def build_dynamic_query(
    parameters: Sequence[str],
    metrics: Sequence[str],
    named_graphs: Sequence[str],
) -> str:
    """Build a SPARQL query for provenance spread across RoHub named graphs."""
    all_names = [*parameters, *metrics]
    var_map = _variable_map(all_names)
    select_vars = " ".join(["?tool_name", _select_variables(all_names, var_map)])

    inner_query = _join_blocks(
        "\n".join(_create_action_links(include_tool=True)),
        "\n".join(
            _parameter_block(name, var_map, FOAF_NAME) for name in parameters
        ),
        "\n".join(_metric_block(name, var_map, FOAF_NAME) for name in metrics),
    )

    order_name = parameters[0] if parameters else None
    return _format_query(
        select_vars,
        _named_graph_values_block(named_graphs, inner_query),
        _order_clause(order_name, var_map),
    )


def configure_rohub(use_production_rohub: bool = False) -> None:
    """Configure RoHub client settings for development or production."""
    environment = "development" if not use_production_rohub else "production"
    config = ROHUB_CONFIG[environment]

    rohub.settings.SLEEP_TIME = ROHUB_CONFIG["sleep_time"]
    rohub.settings.API_URL = config["api_url"]
    rohub.settings.KEYCLOAK_CLIENT_ID = config["keycloak_client_id"]
    rohub.settings.KEYCLOAK_URL = config["keycloak_url"]
    rohub.settings.SPARQL_ENDPOINT = config["sparql_endpoint"]

    if "keycloak_client_secret" in config:
        rohub.settings.KEYCLOAK_CLIENT_SECRET = config["keycloak_client_secret"]


def login_to_rohub(
    username: str,
    password: str,
    use_production_rohub: bool = False,
) -> None:
    """Configure the RoHub client and authenticate with username/password."""
    configure_rohub(use_production_rohub=use_production_rohub)
    rohub.login(username=username, password=password)


def benchmark_annotation_object(benchmark_name: str) -> str:
    """Return the benchmark annotation IRI used for uploaded RO-Crates."""
    return f"{ANNOTATION_CONFIG['benchmark_base_url']}/{benchmark_name}"


def _run_git_command(args: Sequence[str]) -> str | None:
    """Run a git command in the repository root and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    value = result.stdout.strip()
    return value or None


def _normalize_repository_url(repository_url: str | None) -> str | None:
    """Convert common git remote URLs to a GitHub HTTPS repository URL."""
    if not repository_url:
        return None

    repository_url = repository_url.strip().rstrip("/")
    ssh_match = re.match(r"git@([^:]+):(.+)", repository_url)
    if ssh_match:
        repository_url = f"https://{ssh_match.group(1)}/{ssh_match.group(2)}"

    ssh_url_match = re.match(r"ssh://git@([^/]+)/(.+)", repository_url)
    if ssh_url_match:
        repository_url = (
            f"https://{ssh_url_match.group(1)}/{ssh_url_match.group(2)}"
        )

    if repository_url.endswith(".git"):
        repository_url = repository_url[:-4]

    return repository_url


def get_current_branch_name() -> str | None:
    """Return the active branch name from GitHub Actions or local git."""
    for env_name in ("GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
        branch_name = os.environ.get(env_name)
        if branch_name:
            return branch_name

    branch_name = _run_git_command(["branch", "--show-current"])
    if branch_name:
        return branch_name

    branch_name = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch_name and branch_name != "HEAD":
        return branch_name

    return _run_git_command(["rev-parse", "HEAD"])


def get_repository_url(benchmark_name: str | None = None) -> str | None:
    """Return the branchless GitHub repository URL for this benchmark."""
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    if github_repository:
        github_server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        return _normalize_repository_url(f"{github_server_url}/{github_repository}")

    configured_url = ANNOTATION_CONFIG.get("repository_url")
    if configured_url:
        return _normalize_repository_url(configured_url)

    remote_url = _run_git_command(["remote", "get-url", "origin"])
    if remote_url:
        return _normalize_repository_url(remote_url)

    if benchmark_name:
        return _normalize_repository_url(
            f"{ANNOTATION_CONFIG['benchmark_base_url']}/{benchmark_name}"
        )

    return None


def get_current_code_repository_url(benchmark_name: str | None = None) -> str | None:
    """Return the GitHub URL for the current branch or checked-out commit."""
    code_repository_url = os.environ.get("CODE_REPOSITORY_URL")
    if code_repository_url:
        return code_repository_url

    repository_url = get_repository_url(benchmark_name)
    branch_name = get_current_branch_name()
    if repository_url and branch_name:
        return f"{repository_url}/tree/{branch_name}"

    return None


def build_benchmark_ro_uuids_query(benchmark_name: str) -> str:
    """Build a query for research objects annotated with a benchmark IRI."""
    return f"""
    SELECT ?subject
    WHERE {{
      ?subject <{ANNOTATION_PREDICATE}> <{benchmark_annotation_object(benchmark_name)}> .
    }}
    """


def build_annotated_ro_uuids_query(
    benchmark_name: str,
    code_repository_url: str | None = None,
    used_software_url: str | None = None,
) -> str:
    """Build a query for research objects matching upload annotations."""
    annotation_pairs = [
        (ANNOTATION_PREDICATE, benchmark_annotation_object(benchmark_name)),
    ]

    if code_repository_url:
        annotation_pairs.append((CODE_REPOSITORY_PREDICATE, code_repository_url))

    if used_software_url:
        annotation_pairs.append((SOFTWARE_USED_PREDICATE, used_software_url))

    annotation_patterns = "\n".join(
        f"      ?subject <{predicate}> <{value}> ."
        for predicate, value in annotation_pairs
    )

    return f"""
    SELECT ?subject
    WHERE {{ {annotation_patterns} }}
    """

def query_sparql(query: str):
    """Run a SPARQL query against the configured RoHub endpoint."""
    return rohub.query_sparql_endpoint(
        query,
        endpoint_url=rohub.settings.SPARQL_ENDPOINT,
    )


def build_named_graph_query(
    uuid: str,
    use_production_rohub: bool = False,
) -> str:
    """Build a query for the SPARQL named graph of a research object UUID."""
    environment = "production" if use_production_rohub else "development"
    ro_id_base = ROHUB_CONFIG[environment]["ro_id_base"]

    return f"""
    PREFIX schema: <http://schema.org/>
    SELECT ?graph WHERE {{
        GRAPH ?graph {{ <https://w3id.org/{ro_id_base}/{uuid}> a schema:Dataset . }}
    }}
    """


def query_metric_data_from_named_graphs(
    parameters: Sequence[str],
    metrics: Sequence[str],
    named_graphs: Sequence[str],
):
    """Query benchmark parameter and metric data from resolved RoHub graphs."""
    if not named_graphs:
        raise RuntimeError("No RoHub named graphs provided.")

    query = build_dynamic_query(
        parameters,
        metrics,
        named_graphs,
    )
    
    return query_sparql(query)


def filter_by_tool(data: pd.DataFrame, tool: str | None) -> pd.DataFrame:
    """Filter RoHub query results by tool name."""
    if not tool:
        return data

    filtered_df = data[
        data["tool_name"].astype(str).str.lower() == tool.strip().lower()
    ].reset_index(drop=True)

    if filtered_df.empty:
        raise RuntimeError(f"No RoHub data found for tool '{tool}'.")

    return filtered_df


def find_benchmark_ro_uuids(benchmark_name: str) -> list[str]:
    """Find RoHub research object UUIDs annotated with a benchmark IRI."""
    result = query_sparql(build_benchmark_ro_uuids_query(benchmark_name))

    if result.empty:
        return []

    return extract_uuids_from_subjects(result["subject"])


def extract_uuids_from_subjects(subjects: Iterable[str]) -> list[str]:
    """Extract unique UUIDs from RoHub subject IRIs."""
    return list(
        dict.fromkeys(
            str(subject).rstrip("/").split("/")[-1]
            for subject in subjects
        )
    )


def find_annotated_ro_uuids(
    benchmark_name: str,
    code_repository_url: str | None = None,
    used_software_url: str | None = None,
) -> list[str]:
    """Find RoHub research object UUIDs matching upload annotations."""
    result = query_sparql(
        build_annotated_ro_uuids_query(
            benchmark_name=benchmark_name,
            code_repository_url=code_repository_url,
            used_software_url=used_software_url,
        )
    )

    if result.empty:
        return []

    return extract_uuids_from_subjects(result["subject"])


def find_named_graphs_for_uuids(
    uuids: Sequence[str],
    use_production_rohub: bool = False,
) -> dict[str, str]:
    """Find RoHub SPARQL named graphs for research object UUIDs."""
    named_graphs = {}

    for uuid in uuids:
        result = query_sparql(
            build_named_graph_query(
                uuid,
                use_production_rohub=use_production_rohub,
            )
        )

        if not result.empty:
            named_graphs[uuid] = result.iloc[0]["graph"]

    return named_graphs


def fetch_benchmark_data(
    benchmark_name: str,
    parameters: Sequence[str],
    metrics: Sequence[str],
    use_production_rohub: bool = False,
) -> pd.DataFrame:
    """Authenticate with RoHub and fetch benchmark parameter/metric data."""
    code_repository_url = get_current_code_repository_url(benchmark_name)
    if code_repository_url:
        uuids = find_annotated_ro_uuids(
            benchmark_name,
            code_repository_url=code_repository_url,
        )
    else:
        uuids = find_benchmark_ro_uuids(benchmark_name)
    named_graphs = find_named_graphs_for_uuids(
        uuids,
        use_production_rohub=use_production_rohub,
    )

    if not named_graphs:
        raise RuntimeError(
            f"No RoHub named graphs found for benchmark {benchmark_name}."
        )

    result = query_metric_data_from_named_graphs(
        parameters=parameters,
        metrics=metrics,
        named_graphs=list(named_graphs.values()),
    )

    if result.empty:
        raise RuntimeError(
            f"No RoHub metric data found for benchmark {benchmark_name}."
        )

    return result


def load_benchmark_metric_data(
    benchmark_name: str,
    parameters: Sequence[str],
    metrics: Sequence[str],
    tool: str | None = None,
    use_production_rohub: bool = False,
) -> pd.DataFrame:
    """Fetch benchmark metric data from RoHub and optionally filter by tool."""
    configure_rohub(use_production_rohub)
    provenance_df = fetch_benchmark_data(
        benchmark_name=benchmark_name,
        parameters=parameters,
        metrics=metrics,
        use_production_rohub=use_production_rohub,
    )

    return filter_by_tool(provenance_df, tool)


def delete_research_objects_by_annotations(
    benchmark_name: str,
    code_repository_url: str | None = None,
    used_software_url: str | None = None,
) -> None:
    """Delete existing research objects matching upload annotations."""
    uuids = find_annotated_ro_uuids(
        benchmark_name=benchmark_name,
        code_repository_url=code_repository_url,
        used_software_url=used_software_url,
    )

    if not uuids:
        LOGGER.info("No existing annotated research objects found to delete.")
        return

    for uuid in uuids:
        LOGGER.info("Deleting existing annotated research object: %s", uuid)
        try:
            rohub.ros_delete(uuid)
        except SystemExit as e:
            LOGGER.error("Failed to delete research object %s: %s", uuid, e)

def upload_research_object(path_to_zip: str) -> tuple[str, str]:
    """Upload an RO-Crate zip to RoHub and return job id and RO UUID."""
    upload_result = rohub.ros_upload(path_to_zip=path_to_zip)
    job_id = upload_result["identifier"]
    uuid = upload_result["results"].rstrip("/").split("/")[-1]

    return job_id, uuid


def wait_for_job_success(
    job_id: str,
    timeout_seconds: int = 5 * 60,
    poll_interval: int = 10,
) -> bool:
    """Poll a RoHub job until success or timeout."""
    start_time = time.time()

    while True:
        success_result = rohub.is_job_success(job_id=job_id)
        status = success_result.get("status", "UNKNOWN")

        if status == "SUCCESS":
            LOGGER.info("Upload successful: %s", success_result)
            return True

        if time.time() - start_time > timeout_seconds:
            LOGGER.warning(
                "Upload did not succeed within %s seconds. Last status: %s",
                timeout_seconds,
                status,
            )
            return False

        LOGGER.info("Current status: %s, waiting %ss...", status, poll_interval)
        time.sleep(poll_interval)


def add_benchmark_annotation(
    uuid: str,
    benchmark_name: str,
    code_repository_url: str | None = None,
    used_software_url: str | None = None,
) -> None:
    """Add benchmark semantic annotations to a RoHub research object."""
    research_object = rohub.ros_load(uuid)
    annotation_json = [
        {
            "property": ANNOTATION_PREDICATE,
            "value": benchmark_annotation_object(benchmark_name),
        }
    ]

    if code_repository_url:
        annotation_json.append(
            {
                "property": CODE_REPOSITORY_PREDICATE,
                "value": code_repository_url,
            }
        )

    if used_software_url:
        annotation_json.append(
            {
                "property": SOFTWARE_USED_PREDICATE,
                "value": used_software_url,
            }
        )

    add_annotations_result = research_object.add_annotations(
        body_specification_json=annotation_json
    )
    LOGGER.info("Annotations added: %s", add_annotations_result)


def upload_provenance_rocrate(
    provenance_folderpath: str,
    benchmark_name: str,
    username: str,
    password: str,
    rocrate_title: str,
    code_repository_url: str | None = None,
    used_software_url: str | None = None,
    use_production_rohub: bool = False,
) -> str:
    """Upload a provenance RO-Crate to RoHub and add semantic annotations."""
    _ = rocrate_title
    code_repository_url = code_repository_url or get_current_code_repository_url(
        benchmark_name
    )

    login_to_rohub(
        username=username,
        password=password,
        use_production_rohub=use_production_rohub,
    )

    delete_research_objects_by_annotations(
        benchmark_name=benchmark_name,
        code_repository_url=code_repository_url,
        used_software_url=used_software_url,
    )
    job_id, uuid = upload_research_object(provenance_folderpath)

    if wait_for_job_success(job_id):
        add_benchmark_annotation(
            uuid,
            benchmark_name,
            code_repository_url=code_repository_url,
            used_software_url=used_software_url,
        )

    return uuid
